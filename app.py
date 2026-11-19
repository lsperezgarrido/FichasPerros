"""Aplicación Flask local de FichasPerros."""

import io
from datetime import datetime

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError

import database
import ficha_service
import pdf_generator
import whatsapp_import

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = whatsapp_import.MAX_BYTES_ZIP
database.init_db()

DATOS_FICHA_VACIOS = {campo: "" for campo in ficha_service.CAMPOS_FICHA}
MENSAJES_ESTADO = {
    "creada": "Ficha creada correctamente.",
    "actualizada": "Ficha actualizada correctamente.",
    "eliminada": "Ficha eliminada. Sus fotografías siguen en la biblioteca.",
}


@app.template_filter("fecha")
def formatear_fecha(valor):
    """Muestra una fecha ISO en formato español."""
    if not valor:
        return "—"
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor)


@app.template_filter("fecha_hora")
def formatear_fecha_hora(valor):
    """Muestra una marca de tiempo de SQLite en formato español."""
    if not valor:
        return "—"
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d %H:%M:%S").strftime(
            "%d/%m/%Y %H:%M"
        )
    except (TypeError, ValueError):
        return str(valor)


def _pagina(resultado=None, error=None, codigo=200):
    return (
        render_template(
            "index.html",
            resultado=resultado,
            error=error,
            fotos=database.listar_fotos(),
        ),
        codigo,
    )


def _datos_formulario_ficha() -> dict:
    return {
        campo: request.form.get(campo, "")
        for campo in ficha_service.CAMPOS_FICHA
    }


def _fotos_a_quitar() -> set[int]:
    ids = set()
    for valor in request.form.getlist("quitar_fotos"):
        try:
            ids.add(int(valor))
        except (TypeError, ValueError):
            continue
    return ids


def _render_formulario_ficha(
    modo,
    ficha,
    datos,
    fotos_ficha,
    quitar_ids,
    error=None,
    codigo=200,
):
    accion = (
        url_for("crear_ficha")
        if modo == "crear"
        else url_for("actualizar_ficha", ficha_id=ficha["id"])
    )
    return (
        render_template(
            "ficha_formulario.html",
            modo=modo,
            ficha=ficha,
            datos=datos,
            fotos_ficha=fotos_ficha,
            quitar_ids=quitar_ids,
            accion=accion,
            error=error,
        ),
        codigo,
    )


@app.get("/")
def index():
    """Muestra la pantalla principal con la galería."""
    return _pagina()


@app.get("/fichas")
def lista_fichas():
    """Lista y busca las fichas existentes."""
    busqueda = request.args.get("q", "").strip()
    mensaje = MENSAJES_ESTADO.get(request.args.get("estado", ""))
    return render_template(
        "fichas_lista.html",
        fichas=database.listar_fichas(busqueda),
        busqueda=busqueda,
        mensaje=mensaje,
    )


@app.get("/fichas/nueva")
def nueva_ficha():
    """Muestra el formulario de creación de una ficha."""
    return _render_formulario_ficha(
        "crear",
        None,
        dict(DATOS_FICHA_VACIOS),
        [],
        set(),
    )


@app.post("/fichas/nueva")
def crear_ficha():
    """Crea una ficha con sus fotografías."""
    datos = _datos_formulario_ficha()
    try:
        ficha_id = ficha_service.crear_ficha(
            datos,
            request.files.getlist("fotografias"),
        )
    except ficha_service.ErrorFicha as exc:
        return _render_formulario_ficha(
            "crear", None, datos, [], set(), str(exc), 400
        )
    except Exception:
        app.logger.exception("Error inesperado al crear una ficha")
        return _render_formulario_ficha(
            "crear",
            None,
            datos,
            [],
            set(),
            "No se pudo guardar la ficha. Inténtalo de nuevo.",
            500,
        )
    return redirect(
        url_for("detalle_ficha", ficha_id=ficha_id, estado="creada")
    )


@app.get("/fichas/<int:ficha_id>")
def detalle_ficha(ficha_id: int):
    """Muestra todos los datos y fotografías de una ficha."""
    ficha = database.obtener_ficha(ficha_id)
    if ficha is None:
        abort(404)
    mensaje = MENSAJES_ESTADO.get(request.args.get("estado", ""))
    return render_template(
        "ficha_detalle.html",
        ficha=ficha,
        fotos_ficha=database.listar_fotos_ficha(ficha_id),
        mensaje=mensaje,
    )


@app.get("/fichas/<int:ficha_id>/editar")
def editar_ficha(ficha_id: int):
    """Muestra el formulario de edición de una ficha."""
    ficha = database.obtener_ficha(ficha_id)
    if ficha is None:
        abort(404)
    datos = {campo: ficha[campo] for campo in ficha_service.CAMPOS_FICHA}
    return _render_formulario_ficha(
        "editar",
        ficha,
        datos,
        database.listar_fotos_ficha(ficha_id),
        set(),
    )


@app.post("/fichas/<int:ficha_id>/editar")
def actualizar_ficha(ficha_id: int):
    """Actualiza una ficha, añade fotos y quita asociaciones."""
    ficha = database.obtener_ficha(ficha_id)
    if ficha is None:
        abort(404)

    datos = _datos_formulario_ficha()
    quitar_ids = _fotos_a_quitar()
    try:
        ficha_service.actualizar_ficha(
            ficha_id,
            datos,
            request.files.getlist("fotografias"),
            quitar_ids,
        )
    except ficha_service.ErrorFicha as exc:
        return _render_formulario_ficha(
            "editar",
            ficha,
            datos,
            database.listar_fotos_ficha(ficha_id),
            quitar_ids,
            str(exc),
            400,
        )
    except Exception:
        app.logger.exception("Error inesperado al actualizar una ficha")
        return _render_formulario_ficha(
            "editar",
            ficha,
            datos,
            database.listar_fotos_ficha(ficha_id),
            quitar_ids,
            "No se pudo actualizar la ficha. Inténtalo de nuevo.",
            500,
        )
    return redirect(
        url_for("detalle_ficha", ficha_id=ficha_id, estado="actualizada")
    )


@app.get("/fichas/<int:ficha_id>/eliminar")
def confirmar_eliminar_ficha(ficha_id: int):
    """Muestra la confirmación antes de eliminar una ficha."""
    ficha = database.obtener_ficha(ficha_id)
    if ficha is None:
        abort(404)
    return render_template(
        "ficha_eliminar.html",
        ficha=ficha,
        num_fotos=len(database.listar_fotos_ficha(ficha_id)),
    )


@app.post("/fichas/<int:ficha_id>/eliminar")
def eliminar_ficha(ficha_id: int):
    """Elimina una ficha sin tocar fotografías ni PDF históricos."""
    if not ficha_service.eliminar_ficha(ficha_id):
        abort(404)
    return redirect(url_for("lista_fichas", estado="eliminada"))


@app.post("/importar")
def importar():
    """Importa las fotografías de un ZIP subido por el usuario."""
    archivo = request.files.get("archivo_zip")
    if archivo is None or not archivo.filename:
        return _pagina(error="Selecciona un archivo ZIP.", codigo=400)
    if not archivo.filename.lower().endswith(".zip"):
        return _pagina(error="El archivo seleccionado debe ser un ZIP.", codigo=400)

    try:
        resultado = whatsapp_import.importar_zip_whatsapp(archivo.stream)
    except whatsapp_import.ImportacionInvalida as exc:
        return _pagina(error=str(exc), codigo=400)
    except Exception:
        app.logger.exception("Error inesperado durante la importación")
        return _pagina(
            error="No se pudo completar la importación. Revisa el archivo e inténtalo de nuevo.",
            codigo=500,
        )
    return _pagina(resultado=resultado)


@app.get("/fotos/<int:foto_id>/miniatura")
def miniatura(foto_id: int):
    """Sirve una miniatura de una fotografía registrada en SQLite."""
    foto = database.obtener_foto(foto_id)
    if foto is None:
        abort(404)

    directorio_fotos = (database.DATA_DIR / "fotos").resolve()
    ruta = (database.DATA_DIR / foto["ruta"]).resolve()
    if not ruta.is_relative_to(directorio_fotos) or not ruta.is_file():
        abort(404)

    try:
        with Image.open(ruta) as imagen:
            imagen = ImageOps.exif_transpose(imagen)
            imagen.thumbnail((400, 400), Image.Resampling.LANCZOS)
            if imagen.mode in {"RGBA", "LA"} or (
                imagen.mode == "P" and "transparency" in imagen.info
            ):
                imagen = imagen.convert("RGBA")
                fondo = Image.new("RGB", imagen.size, "white")
                fondo.paste(imagen, mask=imagen.getchannel("A"))
                imagen = fondo
            elif imagen.mode != "RGB":
                imagen = imagen.convert("RGB")
            buffer = io.BytesIO()
            imagen.save(buffer, "JPEG", quality=85, optimize=True)
            buffer.seek(0)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ):
        abort(404)

    return send_file(buffer, mimetype="image/jpeg", max_age=3600)


@app.post("/generar-pdf")
def generar_documento_pdf():
    """Genera un PDF nuevo con las fotografías seleccionadas."""
    ids = []
    for valor in request.form.getlist("foto_ids"):
        try:
            foto_id = int(valor)
        except (TypeError, ValueError):
            return jsonify({"error": "La selección de fotografías no es válida."}), 400
        if foto_id not in ids:
            ids.append(foto_id)

    if not ids:
        return jsonify({"error": "Selecciona al menos una fotografía."}), 400

    fotos = []
    for foto_id in ids:
        foto = database.obtener_foto(foto_id)
        if foto is None:
            return (
                jsonify(
                    {
                        "error": (
                            "Alguna fotografía seleccionada ya no está disponible."
                        )
                    }
                ),
                400,
            )
        fotos.append(foto)

    try:
        resultado = pdf_generator.generar_pdf(
            fotos,
            database.DATA_DIR,
            database.BASE_DIR / "documentos",
        )
    except Exception:
        app.logger.exception("Error inesperado durante la generación del PDF")
        return (
            jsonify({"error": "No se pudo generar el PDF. Inténtalo de nuevo."}),
            500,
        )

    return jsonify(
        {
            "nombre": resultado.ruta.name,
            "url": url_for(
                "descargar_documento",
                nombre=resultado.ruta.name,
            ),
            "paginas": resultado.paginas,
            "fichas": resultado.fichas,
        }
    )


@app.get("/documentos/<nombre>")
def descargar_documento(nombre: str):
    """Descarga un documento PDF generado por la aplicación."""
    if not nombre.startswith("fichas_") or not nombre.lower().endswith(".pdf"):
        abort(404)
    return send_from_directory(
        database.BASE_DIR / "documentos",
        nombre,
        as_attachment=True,
        max_age=0,
    )


@app.errorhandler(413)
def archivo_demasiado_grande(_error):
    """Muestra un mensaje claro si Flask rechaza la subida por tamaño."""
    return _pagina(
        error="La subida supera el tamaño máximo permitido (200 MB).",
        codigo=413,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
