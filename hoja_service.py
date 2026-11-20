"""Hoja A4 de cuatro fichas: agrupación, PDF y borrado."""

from __future__ import annotations

from datetime import datetime

import database
import ficha_service
import pdf_generator


def registrar_importacion(foto_ids: list[int]) -> list[int]:
    """Crea una hoja por cada grupo de cuatro fotos recién importadas."""
    mapping = ficha_service.fichas_para_fotos(foto_ids)
    fichas = list(mapping.values())
    hojas = []
    for inicio in range(0, len(fichas), database.POR_HOJA):
        bloque = fichas[inicio : inicio + database.POR_HOJA]
        hoja_id = database.crear_hoja()
        database.vincular_fichas_hoja(hoja_id, bloque)
        hojas.append(hoja_id)
    return hojas


def crear_hoja_para_fichas(ficha_ids: list[int]) -> int:
    """Crea una hoja pendiente con las fichas indicadas."""
    hoja_id = database.crear_hoja()
    database.vincular_fichas_hoja(hoja_id, ficha_ids)
    return hoja_id


def generar_pdf_hoja(hoja_id: int) -> str | None:
    """Genera el PDF de una hoja y devuelve su nombre de archivo."""
    fotos = database.fotos_hoja(hoja_id)
    if not fotos:
        return None
    documento = pdf_generator.generar_pdf(
        fotos,
        database.DATA_DIR,
        database.DOCUMENTOS_DIR,
    )
    database.actualizar_pdf_hoja(
        hoja_id,
        documento.ruta.name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    return documento.ruta.name


def eliminar_hoja(hoja_id: int) -> bool:
    """Borra la hoja y su PDF; las fichas y fotos se conservan."""
    hoja = database.obtener_hoja(hoja_id)
    if hoja is None:
        return False
    if hoja["nombre_pdf"]:
        (database.DOCUMENTOS_DIR / hoja["nombre_pdf"]).unlink(missing_ok=True)
    return database.eliminar_hoja(hoja_id)


def invalidar_pdf_hoja(ficha_id: int) -> None:
    """Deja pendiente la hoja de un perro que se ha eliminado."""
    database.invalidar_pdf_hoja(ficha_id)
