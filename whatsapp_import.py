"""Importación segura de fotografías desde exportaciones ZIP de WhatsApp."""

from __future__ import annotations

import hashlib
import io
import sqlite3
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

import database

EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
FORMATOS_IMAGEN = {"JPEG", "PNG", "WEBP"}
EXTENSION_POR_FORMATO = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

MAX_BYTES_ZIP = 200 * 1024 * 1024
MAX_BYTES_ZIP_DESCOMPRIMIDO = 500 * 1024 * 1024
MAX_ENTRADAS_ZIP = 2000
MAX_BYTES_IMAGEN = 20 * 1024 * 1024
MAX_PIXELES_IMAGEN = 50_000_000


class ImportacionInvalida(ValueError):
    """El ZIP no es válido o contiene elementos potencialmente peligrosos."""


@dataclass
class ResultadoImportacion:
    """Resumen de una importación."""

    encontradas: int = 0
    nuevas: int = 0
    duplicadas: int = 0
    descartadas: int = 0
    errores: int = 0


def importar_zip_whatsapp(origen: str | Path | BinaryIO) -> ResultadoImportacion:
    """Importa las fotografías nuevas de un ZIP de WhatsApp.

    ``origen`` puede ser una ruta o un archivo binario abierto. Los archivos
    solo se leen del ZIP; nunca se extraen ni se ejecutan sus contenidos.
    """
    tamano = _tamano_origen(origen)
    if tamano is not None and tamano > MAX_BYTES_ZIP:
        raise ImportacionInvalida("El archivo ZIP supera el tamaño máximo permitido.")

    try:
        with zipfile.ZipFile(origen) as archivo_zip:
            return _importar_desde_zip(archivo_zip)
    except zipfile.BadZipFile as exc:
        raise ImportacionInvalida("El archivo no es un ZIP válido.") from exc


def _tamano_origen(origen: str | Path | BinaryIO) -> int | None:
    if isinstance(origen, (str, Path)):
        return Path(origen).stat().st_size
    try:
        posicion = origen.tell()
        origen.seek(0, 2)
        tamano = origen.tell()
        origen.seek(posicion)
        return tamano
    except (AttributeError, OSError):
        return None


def _importar_desde_zip(archivo_zip: zipfile.ZipFile) -> ResultadoImportacion:
    _validar_estructura_zip(archivo_zip)
    resultado = ResultadoImportacion()
    fotos_dir = database.DATA_DIR / "fotos"
    fotos_dir.mkdir(parents=True, exist_ok=True)

    conexion = database.get_connection()
    archivos_creados: list[Path] = []
    try:
        hashes_existentes = {
            fila["hash_sha256"]
            for fila in conexion.execute("SELECT hash_sha256 FROM fotos")
        }
        hashes_vistos: set[str] = set()
        registros: list[tuple[str, str, str]] = []
        candidatas = [
            info
            for info in archivo_zip.infolist()
            if not info.is_dir()
            and PurePosixPath(info.filename).suffix.lower() in EXTENSIONES_IMAGEN
        ]
        resultado.encontradas = len(candidatas)

        for info in candidatas:
            if info.file_size > MAX_BYTES_IMAGEN:
                resultado.descartadas += 1
                continue
            try:
                datos = _leer_miembro(archivo_zip, info)
            except Exception:
                resultado.errores += 1
                continue
            if datos is None:
                resultado.descartadas += 1
                continue

            formato = _validar_imagen(datos)
            if formato is None:
                resultado.descartadas += 1
                continue

            hash_sha256 = hashlib.sha256(datos).hexdigest()
            if hash_sha256 in hashes_existentes or hash_sha256 in hashes_vistos:
                resultado.duplicadas += 1
                continue

            nombre_interno, ruta_fisica = _guardar_imagen(datos, formato, fotos_dir)
            archivos_creados.append(ruta_fisica)
            nombre_original = PurePosixPath(info.filename).name
            registros.append(
                (nombre_original, f"fotos/{nombre_interno}", hash_sha256)
            )
            hashes_vistos.add(hash_sha256)
            resultado.nuevas += 1

        if registros:
            with conexion:
                conexion.executemany(
                    "INSERT INTO fotos (nombre_archivo, ruta, hash_sha256) "
                    "VALUES (?, ?, ?)",
                    registros,
                )
        return resultado
    except Exception:
        for ruta in archivos_creados:
            ruta.unlink(missing_ok=True)
        raise
    finally:
        conexion.close()


def _validar_estructura_zip(archivo_zip: zipfile.ZipFile) -> None:
    infos = archivo_zip.infolist()
    if len(infos) > MAX_ENTRADAS_ZIP:
        raise ImportacionInvalida("El ZIP contiene demasiados archivos.")

    total_descomprimido = 0
    for info in infos:
        if not _nombre_seguro(info.filename):
            raise ImportacionInvalida(
                "El ZIP contiene una ruta de archivo no permitida."
            )
        if info.is_dir():
            continue
        total_descomprimido += info.file_size
        if total_descomprimido > MAX_BYTES_ZIP_DESCOMPRIMIDO:
            raise ImportacionInvalida(
                "El contenido descomprimido del ZIP es demasiado grande."
            )


def _nombre_seguro(nombre: str) -> bool:
    """Comprueba que el nombre no pueda escapar del directorio de trabajo."""
    if not nombre or "\x00" in nombre or "\\" in nombre:
        return False
    ruta = PurePosixPath(nombre)
    if ruta.is_absolute():
        return False
    if any(parte in {"", ".", ".."} for parte in ruta.parts):
        return False
    if ":" in ruta.parts[0]:
        return False
    return True


def _leer_miembro(archivo_zip: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes | None:
    with archivo_zip.open(info) as archivo:
        datos = archivo.read(MAX_BYTES_IMAGEN + 1)
    if len(datos) > MAX_BYTES_IMAGEN:
        return None
    return datos


def _validar_imagen(datos: bytes) -> str | None:
    """Devuelve el formato real de la imagen o ``None`` si no es válida."""
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            if imagen.format not in FORMATOS_IMAGEN:
                return None
            if imagen.width * imagen.height > MAX_PIXELES_IMAGEN:
                return None
            imagen.verify()

        with Image.open(io.BytesIO(datos)) as imagen:
            if imagen.format not in FORMATOS_IMAGEN:
                return None
            if imagen.width * imagen.height > MAX_PIXELES_IMAGEN:
                return None
            imagen.load()
            return imagen.format
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None


def _guardar_imagen(datos: bytes, formato: str, fotos_dir: Path) -> tuple[str, Path]:
    """Guarda los bytes originales con un nombre interno único."""
    extension = EXTENSION_POR_FORMATO[formato]
    while True:
        nombre = f"{uuid.uuid4().hex}{extension}"
        ruta = fotos_dir / nombre
        try:
            archivo = ruta.open("xb")
        except FileExistsError:
            continue
        break

    try:
        with archivo:
            archivo.write(datos)
    except Exception:
        ruta.unlink(missing_ok=True)
        raise
    return nombre, ruta
