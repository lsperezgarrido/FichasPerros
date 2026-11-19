"""Aplicación Flask local de FichasPerros."""

from flask import Flask, render_template, request

import database
import whatsapp_import

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = whatsapp_import.MAX_BYTES_ZIP
database.init_db()


def _pagina(resultado=None, error=None, codigo=200):
    return (
        render_template("index.html", resultado=resultado, error=error),
        codigo,
    )


@app.get("/")
def index():
    """Muestra la pantalla principal."""
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


@app.errorhandler(413)
def archivo_demasiado_grande(_error):
    """Muestra un mensaje claro si Flask rechaza la subida por tamaño."""
    return _pagina(
        error="El archivo ZIP supera el tamaño máximo permitido (200 MB).",
        codigo=413,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
