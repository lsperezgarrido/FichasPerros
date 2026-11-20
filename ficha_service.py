"""Operaciones de creación, edición y borrado de fichas."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import date
from pathlib import Path

import database
import whatsapp_import

CAMPOS_FICHA = (
    "lugar_recogida",
    "fecha_recogida",
    "numero_microchip",
    "observaciones",
)
MAX_LONGITUDES = {
    "lugar_recogida": 120,
    "fecha_recogida": 10,
    "numero_microchip": 50,
    "observaciones": 5000,
}
PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErrorFicha(ValueError):
    """Los datos de la ficha o sus fotografías no son válidos."""


def normalizar_datos(datos_crudos: dict) -> dict:
    """Limpia y valida los campos de una ficha."""
    datos = {
        campo: str(datos_crudos.get(campo) or "").strip()
        for campo in CAMPOS_FICHA
    }
    for campo, limite in MAX_LONGITUDES.items():
        if len(datos[campo]) > limite:
            raise ErrorFicha(f"El campo {campo} es demasiado largo.")

    fecha = datos["fecha_recogida"]
    if fecha:
        if not PATRON_FECHA.match(fecha):
            raise ErrorFicha("La fecha de recogida no es válida.")
        try:
            date.fromisoformat(fecha)
        except ValueError as exc:
            raise ErrorFicha("La fecha de recogida no es válida.") from exc
    return datos


def crear_ficha(datos_crudos: dict, archivos) -> int:
    """Crea una ficha y asocia las fotografías subidas."""
    datos = normalizar_datos(datos_crudos)
    fotos = preparar_fotos(archivos)

    conexion = database.get_connection()
    archivos_creados: list[Path] = []
    try:
        with conexion:
            cursor = conexion.execute(
                "INSERT INTO fichas "
                "(lugar_recogida, fecha_recogida, numero_microchip, observaciones) "
                "VALUES (?, ?, ?, ?)",
                (
                    datos["lugar_recogida"],
                    datos["fecha_recogida"],
                    datos["numero_microchip"],
                    datos["observaciones"],
                ),
            )
            ficha_id = cursor.lastrowid
            _agregar_fotos(conexion, ficha_id, fotos, archivos_creados)
        return ficha_id
    except Exception:
        _eliminar_archivos(archivos_creados)
        raise
    finally:
        conexion.close()


def _mapear_fotos_a_fichas(conexion, foto_ids: list[int]):
    """Devuelve ``{foto_id: ficha_id}`` y el número de fichas creadas."""
    mapping: dict[int, int] = {}
    creadas = 0
    for foto_id in dict.fromkeys(foto_ids):
        existe = conexion.execute(
            "SELECT 1 FROM fotos WHERE id = ?", (foto_id,)
        ).fetchone()
        if existe is None:
            continue
        vinculada = conexion.execute(
            "SELECT ficha_id FROM ficha_fotos WHERE foto_id = ? LIMIT 1",
            (foto_id,),
        ).fetchone()
        if vinculada is not None:
            mapping[foto_id] = vinculada["ficha_id"]
            continue
        cursor = conexion.execute(
            "INSERT INTO fichas "
            "(lugar_recogida, fecha_recogida, numero_microchip, observaciones) "
            "VALUES ('', '', '', '')"
        )
        conexion.execute(
            "INSERT INTO ficha_fotos (ficha_id, foto_id, orden) "
            "VALUES (?, ?, 0)",
            (cursor.lastrowid, foto_id),
        )
        mapping[foto_id] = cursor.lastrowid
        creadas += 1
    return mapping, creadas


def fichas_para_fotos(foto_ids: list[int]) -> dict[int, int]:
    """Devuelve la ficha de cada foto, creándola si todavía no existe."""
    conexion = database.get_connection()
    try:
        with conexion:
            mapping, _ = _mapear_fotos_a_fichas(conexion, foto_ids)
        return mapping
    finally:
        conexion.close()


def asegurar_fichas_para_fotos(foto_ids: list[int]) -> int:
    """Crea una ficha por cada foto que todavía no tenga una.

    Devuelve el número de fichas creadas; las fotos que ya tenían ficha se
    reutilizan para no duplicar perros.
    """
    conexion = database.get_connection()
    try:
        with conexion:
            _, creadas = _mapear_fotos_a_fichas(conexion, foto_ids)
        return creadas
    finally:
        conexion.close()


def actualizar_ficha(
    ficha_id: int,
    datos_crudos: dict,
    archivos,
    quitar_foto_ids: set[int],
) -> None:
    """Actualiza los datos y las fotografías asociadas a una ficha."""
    datos = normalizar_datos(datos_crudos)
    fotos = preparar_fotos(archivos)

    conexion = database.get_connection()
    archivos_creados: list[Path] = []
    try:
        if conexion.execute(
            "SELECT 1 FROM fichas WHERE id = ?", (ficha_id,)
        ).fetchone() is None:
            raise ErrorFicha("La ficha solicitada no existe.")

        with conexion:
            conexion.execute(
                "UPDATE fichas SET "
                "lugar_recogida = ?, fecha_recogida = ?, "
                "numero_microchip = ?, observaciones = ?, "
                "fecha_modificacion = datetime('now', 'localtime') "
                "WHERE id = ?",
                (
                    datos["lugar_recogida"],
                    datos["fecha_recogida"],
                    datos["numero_microchip"],
                    datos["observaciones"],
                    ficha_id,
                ),
            )
            for foto_id in quitar_foto_ids:
                conexion.execute(
                    "DELETE FROM ficha_fotos "
                    "WHERE ficha_id = ? AND foto_id = ?",
                    (ficha_id, foto_id),
                )
            _agregar_fotos(conexion, ficha_id, fotos, archivos_creados)
            _renumerar_fotos(conexion, ficha_id)
    except Exception:
        _eliminar_archivos(archivos_creados)
        raise
    finally:
        conexion.close()


def eliminar_ficha(ficha_id: int) -> bool:
    """Elimina la ficha y sus vínculos; las fotografías permanecen."""
    conexion = database.get_connection()
    try:
        with conexion:
            cursor = conexion.execute(
                "DELETE FROM fichas WHERE id = ?",
                (ficha_id,),
            )
        return cursor.rowcount > 0
    finally:
        conexion.close()


def preparar_fotos(archivos) -> list[dict]:
    """Valida en memoria todos los archivos antes de escribir nada."""
    preparadas = []
    for archivo in archivos:
        if archivo is None or not archivo.filename:
            continue
        nombre = _nombre_original(archivo.filename)
        extension = Path(nombre).suffix.lower()
        if extension not in whatsapp_import.EXTENSIONES_IMAGEN:
            raise ErrorFicha(f"El archivo {nombre} no tiene un formato admitido.")

        try:
            archivo.stream.seek(0)
            datos = archivo.stream.read(whatsapp_import.MAX_BYTES_IMAGEN + 1)
        except (AttributeError, OSError, ValueError) as exc:
            raise ErrorFicha(f"No se pudo leer el archivo {nombre}.") from exc
        if len(datos) > whatsapp_import.MAX_BYTES_IMAGEN:
            raise ErrorFicha(f"La imagen {nombre} es demasiado grande.")
        formato = whatsapp_import.validar_imagen(datos)
        if formato is None:
            raise ErrorFicha(f"El archivo {nombre} no es una imagen válida.")

        preparadas.append(
            {
                "nombre_original": nombre,
                "datos": datos,
                "formato": formato,
                "hash_sha256": hashlib.sha256(datos).hexdigest(),
            }
        )
    return preparadas


def _nombre_original(nombre: str) -> str:
    nombre = nombre.replace("\\", "/").rsplit("/", 1)[-1]
    nombre = "".join(caracter for caracter in nombre if caracter >= " ").strip()
    return nombre[:255] or "fotografia"


def _agregar_fotos(
    conexion: sqlite3.Connection,
    ficha_id: int,
    fotos: list[dict],
    archivos_creados: list[Path],
) -> None:
    orden = conexion.execute(
        "SELECT COALESCE(MAX(orden), -1) + 1 FROM ficha_fotos WHERE ficha_id = ?",
        (ficha_id,),
    ).fetchone()[0]
    for foto in fotos:
        foto_id = _obtener_o_crear_foto(conexion, foto, archivos_creados)
        cursor = conexion.execute(
            "INSERT OR IGNORE INTO ficha_fotos (ficha_id, foto_id, orden) "
            "VALUES (?, ?, ?)",
            (ficha_id, foto_id, orden),
        )
        if cursor.rowcount:
            orden += 1


def _obtener_o_crear_foto(
    conexion: sqlite3.Connection,
    foto: dict,
    archivos_creados: list[Path],
) -> int:
    existente = conexion.execute(
        "SELECT id FROM fotos WHERE hash_sha256 = ?",
        (foto["hash_sha256"],),
    ).fetchone()
    if existente is not None:
        return existente["id"]

    fotos_dir = database.DATA_DIR / "fotos"
    fotos_dir.mkdir(parents=True, exist_ok=True)
    nombre_interno, ruta = whatsapp_import.guardar_imagen(
        foto["datos"],
        foto["formato"],
        fotos_dir,
    )
    archivos_creados.append(ruta)
    cursor = conexion.execute(
        "INSERT INTO fotos (nombre_archivo, ruta, hash_sha256) "
        "VALUES (?, ?, ?)",
        (
            foto["nombre_original"],
            f"fotos/{nombre_interno}",
            foto["hash_sha256"],
        ),
    )
    return cursor.lastrowid


def _renumerar_fotos(conexion: sqlite3.Connection, ficha_id: int) -> None:
    filas = conexion.execute(
        "SELECT rowid AS fila_id FROM ficha_fotos "
        "WHERE ficha_id = ? ORDER BY orden, rowid",
        (ficha_id,),
    ).fetchall()
    for nuevo_orden, fila in enumerate(filas):
        conexion.execute(
            "UPDATE ficha_fotos SET orden = ? WHERE rowid = ?",
            (nuevo_orden, fila["fila_id"]),
        )


def _eliminar_archivos(rutas: list[Path]) -> None:
    for ruta in rutas:
        ruta.unlink(missing_ok=True)
