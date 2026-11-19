"""Aplicación Flask local de FichasPerros."""

from flask import Flask, render_template

import database

app = Flask(__name__)
database.init_db()


@app.route("/")
def index():
    """Muestra la pantalla principal."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
