"""Acceso a la base de datos SQLite local."""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
EMPAQUETADO = bool(getattr(sys, "frozen", False))
# Carpeta del ejecutable: solo se usa como alternativa si %LOCALAPPDATA% no
# admite escritura (ocurre en algunos equipos con políticas restrictivas).
CARPETA_EJECUTABLE = (
    Path(sys.executable).resolve().parent if EMPAQUETADO else PROJECT_DIR
)


def _directorio_escribible(directorio: Path) -> bool:
    """Comprueba que se puede crear y borrar un archivo en la carpeta."""
    prueba = directorio / ".fichas_perros_write_test"
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink()
        return True
    except OSError:
        return False


def _resolver_directorios(empaquetado: bool, local_appdata: str | None, proyecto: Path):
    """Separa datos persistentes de los recursos del ejecutable."""
    if empaquetado:
        base = Path(local_appdata or Path.home() / "AppData" / "Local") / "FichasPerros"
        return base, base, base / "documentos"
    return proyecto, proyecto / "data", proyecto / "documentos"


# Durante el desarrollo se mantienen las carpetas actuales del proyecto. En un
# ejecutable, la base de datos, las fotos y los PDF van a %LOCALAPPDATA%.
BASE_DIR, DATA_DIR, DOCUMENTOS_DIR = _resolver_directorios(
    EMPAQUETADO,
    os.environ.get("LOCALAPPDATA"),
    PROJECT_DIR,
)

if EMPAQUETADO and not _directorio_escribible(DATA_DIR):
    # El ejecutable no puede escribir en %LOCALAPPDATA%: se conservan los
    # datos junto a él para que la aplicación siga siendo utilizable.
    alternativo = CARPETA_EJECUTABLE / "datos"
    _directorio_escribible(alternativo)
    BASE_DIR = DATA_DIR = alternativo
    DOCUMENTOS_DIR = alternativo / "documentos"

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

CREATE TABLE IF NOT EXISTS hojas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_pdf TEXT,
    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_generacion TEXT
);

CREATE TABLE IF NOT EXISTS hoja_fichas (
    hoja_id INTEGER NOT NULL,
    ficha_id INTEGER NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (hoja_id, ficha_id),
    FOREIGN KEY (hoja_id) REFERENCES hojas(id) ON DELETE CASCADE,
    FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hoja_fichas_ficha
    ON hoja_fichas(ficha_id);

CREATE TABLE IF NOT EXISTS metadata (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""

POR_HOJA = 4


def get_connection():
    """Devuelve una conexión nueva a la base de datos local."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _migrar_hojas(connection):
    """Agrupa las fichas existentes en hojas y asocia los PDF por antigüedad."""
    fichas = connection.execute(
        "SELECT id, fecha_creacion FROM fichas ORDER BY id"
    ).fetchall()
    documentos = sorted(DOCUMENTOS_DIR.glob("fichas_*.pdf"), key=lambda r: r.name)
    indice = 0
    for inicio in range(0, len(fichas), POR_HOJA):
        bloque = fichas[inicio : inicio + POR_HOJA]
        nombre_pdf = None
        fecha_generacion = None
        if indice < len(documentos):
            ruta = documentos[indice]
            nombre_pdf = ruta.name
            fecha_generacion = datetime.fromtimestamp(ruta.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            indice += 1
        cursor = connection.execute(
            "INSERT INTO hojas (nombre_pdf, fecha_creacion, fecha_generacion) "
            "VALUES (?, ?, ?)",
            (nombre_pdf, bloque[0]["fecha_creacion"], fecha_generacion),
        )
        hoja_id = cursor.lastrowid
        for orden, ficha in enumerate(bloque):
            connection.execute(
                "INSERT INTO hoja_fichas (hoja_id, ficha_id, orden) "
                "VALUES (?, ?, ?)",
                (hoja_id, ficha["id"], orden),
            )


def init_db():
    """Crea la base de datos y las tablas si no existen."""
    connection = get_connection()
    try:
        connection.executescript(SCHEMA)
        if connection.execute(
            "SELECT 1 FROM metadata WHERE clave = 'hojas_v1'"
        ).fetchone() is None:
            if connection.execute("SELECT 1 FROM fichas LIMIT 1").fetchone():
                _migrar_hojas(connection)
            connection.execute(
                "INSERT INTO metadata (clave, valor) VALUES ('hojas_v1', '1')"
            )
        connection.commit()
    finally:
        connection.close()


def listar_hojas(busqueda: str = ""):
    """Devuelve las hojas, con número de perros y estado de su PDF."""
    consulta = """
    SELECT h.id, h.nombre_pdf, h.fecha_creacion, h.fecha_generacion,
           COUNT(hf.ficha_id) AS num_perros,
           (
             SELECT f.id FROM hoja_fichas hf2
             JOIN ficha_fotos ff ON ff.ficha_id = hf2.ficha_id
             JOIN fotos f ON f.id = ff.foto_id
             WHERE hf2.hoja_id = h.id
             ORDER BY hf2.orden, ff.orden, ff.rowid
             LIMIT 1
           ) AS foto_portada_id
    FROM hojas h
    LEFT JOIN hoja_fichas hf ON hf.hoja_id = h.id
    """
    parametros = []
    texto = busqueda.strip()
    if texto:
        consulta += (
            " WHERE CAST(h.id AS TEXT) LIKE ? "
            "OR COALESCE(h.nombre_pdf, '') LIKE ? "
            "OR h.fecha_creacion LIKE ?"
        )
        parametros = [f"%{texto}%"] * 3
    consulta += " GROUP BY h.id ORDER BY h.id DESC"
    connection = get_connection()
    try:
        return connection.execute(consulta, parametros).fetchall()
    finally:
        connection.close()


def obtener_hoja(hoja_id: int):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT id, nombre_pdf, fecha_creacion, fecha_generacion "
            "FROM hojas WHERE id = ?",
            (hoja_id,),
        ).fetchone()
    finally:
        connection.close()


def listar_perros_hoja(hoja_id: int):
    """Devuelve los perros de una hoja en el orden en que se imprimen."""
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT fi.id, fi.lugar_recogida, fi.fecha_recogida,
                   fi.numero_microchip, fi.observaciones,
                   (SELECT COUNT(*) FROM ficha_fotos ff
                    WHERE ff.ficha_id = fi.id) AS num_fotos,
                   (SELECT ff.foto_id FROM ficha_fotos ff
                    WHERE ff.ficha_id = fi.id
                    ORDER BY ff.orden, ff.rowid LIMIT 1) AS foto_portada_id
            FROM hoja_fichas hf
            JOIN fichas fi ON fi.id = hf.ficha_id
            WHERE hf.hoja_id = ?
            ORDER BY hf.orden
            """,
            (hoja_id,),
        ).fetchall()
    finally:
        connection.close()


def fotos_hoja(hoja_id: int):
    """Fotografías de la hoja, en orden de impresión."""
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT f.id, f.nombre_archivo, f.ruta
            FROM hoja_fichas hf
            JOIN ficha_fotos ff ON ff.ficha_id = hf.ficha_id
            JOIN fotos f ON f.id = ff.foto_id
            WHERE hf.hoja_id = ?
            ORDER BY hf.orden, ff.orden, ff.rowid
            """,
            (hoja_id,),
        ).fetchall()
    finally:
        connection.close()


def crear_hoja(fecha_creacion: str | None = None) -> int:
    connection = get_connection()
    try:
        with connection:
            if fecha_creacion:
                cursor = connection.execute(
                    "INSERT INTO hojas (fecha_creacion) VALUES (?)",
                    (fecha_creacion,),
                )
            else:
                cursor = connection.execute("INSERT INTO hojas DEFAULT VALUES")
        return cursor.lastrowid
    finally:
        connection.close()


def vincular_fichas_hoja(hoja_id: int, ficha_ids: list[int]) -> None:
    connection = get_connection()
    try:
        with connection:
            connection.executemany(
                "INSERT INTO hoja_fichas (hoja_id, ficha_id, orden) "
                "VALUES (?, ?, ?)",
                [(hoja_id, ficha_id, orden) for orden, ficha_id in enumerate(ficha_ids)],
            )
    finally:
        connection.close()


def actualizar_pdf_hoja(
    hoja_id: int, nombre_pdf: str, fecha_generacion: str
) -> None:
    connection = get_connection()
    try:
        with connection:
            connection.execute(
                "UPDATE hojas SET nombre_pdf = ?, fecha_generacion = ? "
                "WHERE id = ?",
                (nombre_pdf, fecha_generacion, hoja_id),
            )
    finally:
        connection.close()


def invalidar_pdf_hoja(ficha_id: int) -> None:
    """Marca como pendiente la hoja de un perro eliminado."""
    connection = get_connection()
    try:
        with connection:
            connection.execute(
                "UPDATE hojas SET nombre_pdf = NULL, fecha_generacion = NULL "
                "WHERE id IN (SELECT hoja_id FROM hoja_fichas WHERE ficha_id = ?)",
                (ficha_id,),
            )
    finally:
        connection.close()


def eliminar_hoja(hoja_id: int) -> bool:
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute("DELETE FROM hojas WHERE id = ?", (hoja_id,))
        return cursor.rowcount > 0
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
