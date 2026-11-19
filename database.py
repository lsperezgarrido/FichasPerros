"""Acceso a la base de datos SQLite local."""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "fichas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_archivo TEXT NOT NULL,
    ruta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL UNIQUE,
    fecha_importacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_connection():
    """Devuelve una conexión nueva a la base de datos local."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Crea la base de datos y la tabla de fotografías si no existen."""
    connection = get_connection()
    try:
        connection.execute(SCHEMA)
        connection.commit()
    finally:
        connection.close()
