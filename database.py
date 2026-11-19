"""Acceso a la base de datos SQLite local."""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def _resolver_directorios(empaquetado: bool, local_appdata: str | None, proyecto: Path):
    """Separa datos persistentes de los recursos del ejecutable."""
    if empaquetado:
        base = Path(local_appdata or Path.home() / "AppData" / "Local") / "FichasPerros"
        return base, base, base / "documentos"
    return proyecto, proyecto / "data", proyecto / "documentos"


# Durante el desarrollo se mantienen las carpetas actuales del proyecto. En un
# ejecutable, la base de datos, las fotos y los PDF van a %LOCALAPPDATA%.
BASE_DIR, DATA_DIR, DOCUMENTOS_DIR = _resolver_directorios(
    bool(getattr(sys, "frozen", False)),
    os.environ.get("LOCALAPPDATA"),
    PROJECT_DIR,
)
DB_PATH = DATA_DIR / "fichas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_archivo TEXT NOT NULL,
    ruta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL UNIQUE,
    fecha_importacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS fichas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lugar_recogida TEXT NOT NULL DEFAULT '',
    fecha_recogida TEXT NOT NULL DEFAULT '',
    numero_microchip TEXT NOT NULL DEFAULT '',
    observaciones TEXT NOT NULL DEFAULT '',
    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_modificacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ficha_fotos (
    ficha_id INTEGER NOT NULL,
    foto_id INTEGER NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ficha_id, foto_id),
    FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE,
    FOREIGN KEY (foto_id) REFERENCES fotos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ficha_fotos_foto
    ON ficha_fotos(foto_id);
"""


def get_connection():
    """Devuelve una conexión nueva a la base de datos local."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Crea la base de datos y las tablas si no existen."""
    connection = get_connection()
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def listar_fotos():
    """Devuelve todas las fotografías ordenadas por importación."""
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT id, nombre_archivo, ruta, fecha_importacion "
            "FROM fotos ORDER BY id"
        ).fetchall()
    finally:
        connection.close()


def obtener_foto(foto_id: int):
    """Devuelve una fotografía por su identificador o ``None``."""
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT id, nombre_archivo, ruta FROM fotos WHERE id = ?",
            (foto_id,),
        ).fetchone()
    finally:
        connection.close()


def listar_fichas(busqueda: str = ""):
    """Devuelve las fichas, opcionalmente filtradas por texto."""
    consulta = """
SELECT
    fi.id,
    fi.lugar_recogida,
    fi.fecha_recogida,
    fi.numero_microchip,
    fi.observaciones,
    fi.fecha_creacion,
    fi.fecha_modificacion,
    (
        SELECT COUNT(*)
        FROM ficha_fotos ff
        WHERE ff.ficha_id = fi.id
    ) AS num_fotos,
    (
        SELECT ff.foto_id
        FROM ficha_fotos ff
        WHERE ff.ficha_id = fi.id
        ORDER BY ff.orden, ff.rowid
        LIMIT 1
    ) AS foto_portada_id
FROM fichas fi
"""
    parametros = []
    busqueda = busqueda.strip()
    if busqueda:
        patron = f"%{busqueda}%"
        condiciones = [
            "fi.lugar_recogida LIKE ?",
            "fi.fecha_recogida LIKE ?",
            "fi.numero_microchip LIKE ?",
            "fi.observaciones LIKE ?",
            "CAST(fi.id AS TEXT) LIKE ?",
        ]
        parametros = [patron] * 5
        try:
            fecha_iso = datetime.strptime(busqueda, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            fecha_iso = None
        if fecha_iso:
            condiciones.append("fi.fecha_recogida = ?")
            parametros.append(fecha_iso)
        consulta += " WHERE " + " OR ".join(condiciones)
    consulta += " ORDER BY fi.id DESC"

    connection = get_connection()
    try:
        return connection.execute(consulta, parametros).fetchall()
    finally:
        connection.close()


def obtener_ficha(ficha_id: int):
    """Devuelve una ficha por su identificador o ``None``."""
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT id, lugar_recogida, fecha_recogida, numero_microchip, "
            "observaciones, fecha_creacion, fecha_modificacion "
            "FROM fichas WHERE id = ?",
            (ficha_id,),
        ).fetchone()
    finally:
        connection.close()


def listar_fotos_ficha(ficha_id: int):
    """Devuelve las fotografías asociadas a una ficha, en orden."""
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT f.id, f.nombre_archivo, f.ruta "
            "FROM ficha_fotos ff "
            "JOIN fotos f ON f.id = ff.foto_id "
            "WHERE ff.ficha_id = ? "
            "ORDER BY ff.orden, ff.rowid",
            (ficha_id,),
        ).fetchall()
    finally:
        connection.close()
