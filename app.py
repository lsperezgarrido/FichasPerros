"""Aplicación Flask local de FichasPerros."""

import io

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError

import database
import pdf_generator
import whatsapp_import

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = whatsapp_import.MAX_BYTES_ZIP
database.init_db()


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


@app.get("/")
def index():
    """Muestra la pantalla principal con la galería."""
    return _pagina()


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
        error="El archivo ZIP supera el tamaño máximo permitido (200 MB).",
        codigo=413,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
