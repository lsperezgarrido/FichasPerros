"""Generación de fichas imprimibles en PDF."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ANCHO_PAGINA, ALTO_PAGINA = A4
MARGEN = 12 * mm
X0 = MARGEN
Y0 = MARGEN
ANCHO_UTIL = ANCHO_PAGINA - 2 * MARGEN
ALTO_UTIL = ALTO_PAGINA - 2 * MARGEN
ALTO_FICHA = ALTO_UTIL / 4
ANCHO_FICHA = ANCHO_UTIL
ANCHO_FOTO = ANCHO_FICHA / 3
ANCHO_DATOS = ANCHO_FICHA - ANCHO_FOTO
PADDING = 3 * mm
ALTO_DATOS = ALTO_FICHA - 2 * PADDING
ALTO_CAMPO = 12 * mm
ALTO_OBSERVACIONES = ALTO_DATOS - 3 * ALTO_CAMPO

CAMPOS = (
    "LUGAR DE RECOGIDA",
    "FECHA DE RECOGIDA",
    "Nº MICROCHIP",
    "OBSERVACIONES",
)


@dataclass(frozen=True)
class ResultadoPDF:
    """Resultado de una generación de PDF."""

    ruta: Path
    paginas: int
    fichas: int


def generar_pdf(
    fotos: list,
    directorio_datos: str | Path,
    directorio_salida: str | Path,
) -> ResultadoPDF:
    """Genera un PDF nuevo con una ficha por cada fotografía.

    ``fotos`` debe contener filas con las claves ``ruta`` y ``nombre_archivo``.
    Las rutas se resuelven dentro de ``directorio_datos/fotos``.
    """
    fotos = list(fotos)
    if not fotos:
        raise ValueError("No hay fotografías para generar el PDF.")

    base_datos = Path(directorio_datos).resolve()
    base_fotos = (base_datos / "fotos").resolve()
    rutas = []
    for foto in fotos:
        ruta = (base_datos / foto["ruta"]).resolve()
        if not ruta.is_relative_to(base_fotos) or not ruta.is_file():
            raise FileNotFoundError(
                f"No se encontró la fotografía {foto['nombre_archivo']}."
            )
        rutas.append(ruta)

    destino = Path(directorio_salida)
    destino.mkdir(parents=True, exist_ok=True)
    ruta_pdf = _reservar_nombre(destino)

    try:
        _escribir_pdf(rutas, ruta_pdf)
    except Exception:
        ruta_pdf.unlink(missing_ok=True)
        raise

    return ResultadoPDF(
        ruta=ruta_pdf,
        paginas=(len(fotos) + 3) // 4,
        fichas=len(fotos),
    )


def _reservar_nombre(directorio: Path) -> Path:
    while True:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"fichas_{marca}_{uuid.uuid4().hex[:8]}.pdf"
        ruta = directorio / nombre
        try:
            with ruta.open("xb"):
                pass
        except FileExistsError:
            continue
        return ruta


def _escribir_pdf(rutas: list[Path], ruta_pdf: Path) -> None:
    documento = canvas.Canvas(str(ruta_pdf), pagesize=A4, pageCompression=1)
    documento.setTitle("Fichas de perros")
    documento.setAuthor("FichasPerros")
    documento.setSubject("Fichas imprimibles de perros")

    for inicio in range(0, len(rutas), 4):
        _dibujar_marco_pagina(documento)
        for posicion in range(4):
            indice = inicio + posicion
            if indice >= len(rutas):
                continue
            y_inferior = Y0 + (3 - posicion) * ALTO_FICHA
            _dibujar_ficha(documento, rutas[indice], y_inferior)
        documento.showPage()

    documento.save()


def _dibujar_marco_pagina(documento: canvas.Canvas) -> None:
    documento.setStrokeGray(0.25)
    documento.setLineWidth(0.7)
    documento.rect(X0, Y0, ANCHO_UTIL, ALTO_UTIL, stroke=1, fill=0)
    documento.setLineWidth(0.55)
    for separacion in range(1, 4):
        y = Y0 + separacion * ALTO_FICHA
        documento.line(X0, y, X0 + ANCHO_UTIL, y)


def _dibujar_ficha(documento: canvas.Canvas, ruta_foto: Path, y_inferior: float) -> None:
    x_separador = X0 + ANCHO_FOTO
    documento.setStrokeGray(0.35)
    documento.setLineWidth(0.5)
    documento.line(
        x_separador,
        y_inferior,
        x_separador,
        y_inferior + ALTO_FICHA,
    )

    x_foto = X0 + PADDING
    y_foto = y_inferior + PADDING
    ancho_foto = ANCHO_FOTO - 2 * PADDING
    alto_foto = ALTO_FICHA - 2 * PADDING
    try:
        with Image.open(ruta_foto) as imagen:
            # Recortar el centro a la misma proporción que el marco para que la
            # foto lo cubra por completo, sin bandas blancas ni deformación.
            relacion_marco = ancho_foto / alto_foto
            relacion_imagen = imagen.width / imagen.height
            if relacion_imagen > relacion_marco:
                nuevo_ancho = round(imagen.height * relacion_marco)
                izquierda = (imagen.width - nuevo_ancho) // 2
                recortada = imagen.crop(
                    (izquierda, 0, izquierda + nuevo_ancho, imagen.height)
                )
            elif relacion_imagen < relacion_marco:
                nuevo_alto = round(imagen.width / relacion_marco)
                arriba = (imagen.height - nuevo_alto) // 2
                recortada = imagen.crop(
                    (0, arriba, imagen.width, arriba + nuevo_alto)
                )
            else:
                recortada = imagen
            documento.drawImage(
                ImageReader(recortada),
                x_foto,
                y_foto,
                width=ancho_foto,
                height=alto_foto,
                preserveAspectRatio=False,
                mask="auto",
            )
    except Exception as exc:
        raise ValueError(
            f"No se pudo incluir la fotografía {ruta_foto.name} en el PDF."
        ) from exc

    _dibujar_campos(documento, x_separador + PADDING, y_inferior)


def _dibujar_campos(documento: canvas.Canvas, x: float, y_inferior: float) -> None:
    ancho = ANCHO_DATOS - 2 * PADDING
    arriba = y_inferior + ALTO_FICHA - PADDING

    documento.setStrokeGray(0.55)
    documento.setLineWidth(0.35)
    documento.setFillGray(0.2)
    documento.setFont("Helvetica-Bold", 8)

    for indice, nombre in enumerate(CAMPOS[:3]):
        y_superior = arriba - indice * ALTO_CAMPO
        documento.rect(
            x,
            y_superior - ALTO_CAMPO,
            ancho,
            ALTO_CAMPO,
            stroke=1,
            fill=0,
        )
        documento.drawString(x + 2 * mm, y_superior - 3.6 * mm, nombre)

    y_observaciones = arriba - 3 * ALTO_CAMPO
    documento.rect(
        x,
        y_observaciones - ALTO_OBSERVACIONES,
        ancho,
        ALTO_OBSERVACIONES,
        stroke=1,
        fill=0,
    )
    documento.drawString(
        x + 2 * mm,
        y_observaciones - 3.6 * mm,
        CAMPOS[3],
    )
