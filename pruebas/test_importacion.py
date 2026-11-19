"""Pruebas de la importación de exportaciones ZIP de WhatsApp."""

from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import database  # noqa: E402
import whatsapp_import  # noqa: E402

ZIP1 = BASE_DIR / "pruebas" / "exportacion_whatsapp_01.zip"
ZIP2 = BASE_DIR / "pruebas" / "exportacion_whatsapp_02.zip"
IMAGENES_ZIP1 = [
    "IMG-20240115-WA0001.jpg",
    "IMG-20240115-WA0002.jpg",
    "IMG-20240115-WA0003.jpg",
    "IMG-20240115-WA0004.jpg",
    "IMG-20240115-WA0005.png",
    "IMG-20240115-WA0006.webp",
    "IMG-20240115-WA0007.jpeg",
]
DUPLICADAS_ZIP2 = [
    ("IMG-20240115-WA0001.jpg", "IMG-20240220-WA0010.jpg"),
    ("IMG-20240115-WA0003.jpg", "IMG-20240220-WA0011.jpg"),
    ("IMG-20240115-WA0005.png", "IMG-20240220-WA0012.png"),
    ("IMG-20240115-WA0006.webp", "IMG-20240220-WA0013.webp"),
    ("IMG-20240115-WA0007.jpeg", "IMG-20240220-WA0014.jpeg"),
]
NUEVAS_ZIP2 = [
    "IMG-20240220-WA0015.jpg",
    "IMG-20240220-WA0016.png",
    "IMG-20240220-WA0017.webp",
]


class ImportacionWhatsAppTests(unittest.TestCase):
    """Comprueba los recuentos, la persistencia y los rechazos de seguridad."""

    def setUp(self):
        self._directorio_original = database.DATA_DIR
        self._db_original = database.DB_PATH
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.addCleanup(self._restaurar_database)

        database.DATA_DIR = Path(self.temporal.name) / "data"
        database.DB_PATH = database.DATA_DIR / "fichas.db"
        database.init_db()
        self.fotos_dir = database.DATA_DIR / "fotos"
        self.hash_zip1_original = hashlib.sha256(ZIP1.read_bytes()).hexdigest()
        self.hash_zip2_original = hashlib.sha256(ZIP2.read_bytes()).hexdigest()

    def _restaurar_database(self):
        database.DATA_DIR = self._directorio_original
        database.DB_PATH = self._db_original

    def _filas(self):
        conexion = database.get_connection()
        try:
            return conexion.execute(
                "SELECT nombre_archivo, ruta, hash_sha256 FROM fotos ORDER BY id"
            ).fetchall()
        finally:
            conexion.close()

    def _contar_fotos(self) -> int:
        conexion = database.get_connection()
        try:
            return conexion.execute("SELECT COUNT(*) FROM fotos").fetchone()[0]
        finally:
            conexion.close()

    def _importar(self, archivo):
        if isinstance(archivo, Path):
            return whatsapp_import.importar_zip_whatsapp(archivo)
        with archivo.open("rb") as manejador:
            return whatsapp_import.importar_zip_whatsapp(manejador)

    def test_importar_zip1(self):
        resultado = self._importar(ZIP1)
        self.assertEqual(resultado.encontradas, 7)
        self.assertEqual(resultado.nuevas, 7)
        self.assertEqual(resultado.duplicadas, 0)
        self.assertEqual(resultado.descartadas, 0)
        self.assertEqual(resultado.errores, 0)
        self.assertEqual(self._contar_fotos(), 7)

    def test_reimportar_zip1(self):
        self._importar(ZIP1)
        resultado = self._importar(ZIP1)
        self.assertEqual(resultado.encontradas, 7)
        self.assertEqual(resultado.nuevas, 0)
        self.assertEqual(resultado.duplicadas, 7)
        self.assertEqual(resultado.descartadas, 0)
        self.assertEqual(resultado.errores, 0)
        self.assertEqual(self._contar_fotos(), 7)

    def test_importar_zip2_con_duplicados_y_nuevas(self):
        self._importar(ZIP1)
        resultado = self._importar(ZIP2)
        self.assertEqual(resultado.encontradas, 8)
        self.assertEqual(resultado.nuevas, 3)
        self.assertEqual(resultado.duplicadas, 5)
        self.assertEqual(resultado.descartadas, 0)
        self.assertEqual(resultado.errores, 0)
        self.assertEqual(self._contar_fotos(), 10)

    def test_total_de_diez_fotos_unicas(self):
        for _ in range(2):
            self._importar(ZIP1)
        self._importar(ZIP2)
        self.assertEqual(self._contar_fotos(), 10)
        filas = self._filas()
        self.assertEqual(len({fila["hash_sha256"] for fila in filas}), 10)
        self.assertEqual(len(list(self.fotos_dir.iterdir())), 10)
        self.assertEqual(
            {fila["nombre_archivo"] for fila in filas},
            set(IMAGENES_ZIP1) | set(NUEVAS_ZIP2),
        )
        for fila in filas:
            self.assertTrue(fila["ruta"].startswith("fotos/"))
            self.assertNotEqual(fila["ruta"], fila["nombre_archivo"])

    def test_fotos_guardadas_se_abren_y_conservan_su_hash(self):
        self._importar(ZIP1)
        self._importar(ZIP2)
        filas = self._filas()
        self.assertEqual(len(filas), 10)
        for fila in filas:
            ruta = database.DATA_DIR / fila["ruta"]
            self.assertTrue(ruta.is_file(), ruta)
            self.assertEqual(
                hashlib.sha256(ruta.read_bytes()).hexdigest(), fila["hash_sha256"]
            )
            with Image.open(ruta) as imagen:
                imagen.load()
                self.assertGreater(imagen.width, 0)
                self.assertGreater(imagen.height, 0)

        hashes_origen = set()
        for archivo_zip in (ZIP1, ZIP2):
            with zipfile.ZipFile(archivo_zip) as archivo:
                for nombre in archivo.namelist():
                    if Path(nombre).suffix.lower() in whatsapp_import.EXTENSIONES_IMAGEN:
                        hashes_origen.add(
                            hashlib.sha256(archivo.read(nombre)).hexdigest()
                        )
        self.assertEqual({fila["hash_sha256"] for fila in filas}, hashes_origen)

    def test_los_zip_originales_no_se_modifican(self):
        self._importar(ZIP1)
        self._importar(ZIP2)
        self.assertEqual(
            hashlib.sha256(ZIP1.read_bytes()).hexdigest(), self.hash_zip1_original
        )
        self.assertEqual(
            hashlib.sha256(ZIP2.read_bytes()).hexdigest(), self.hash_zip2_original
        )

        with zipfile.ZipFile(ZIP1) as archivo1, zipfile.ZipFile(ZIP2) as archivo2:
            for nombre1, nombre2 in DUPLICADAS_ZIP2:
                self.assertEqual(archivo1.read(nombre1), archivo2.read(nombre2))

    def test_zip_slip_se_rechaza_sin_importar(self):
        archivo_malicioso = Path(self.temporal.name) / "malicioso.zip"
        with zipfile.ZipFile(archivo_malicioso, "w") as archivo:
            archivo.writestr("chat.txt", "exportación")
            with zipfile.ZipFile(ZIP1) as original:
                imagen = original.read(IMAGENES_ZIP1[0])
            archivo.writestr("../fuera.jpg", imagen)

        with self.assertRaises(whatsapp_import.ImportacionInvalida):
            whatsapp_import.importar_zip_whatsapp(archivo_malicioso)
        self.assertEqual(self._contar_fotos(), 0)
        if self.fotos_dir.exists():
            self.assertEqual(len(list(self.fotos_dir.iterdir())), 0)
        self.assertFalse((Path(self.temporal.name) / "fuera.jpg").exists())

    def test_archivo_que_no_es_zip_se_rechaza(self):
        falso_zip = Path(self.temporal.name) / "falso.zip"
        falso_zip.write_text("esto no es un ZIP", encoding="utf-8")
        with self.assertRaises(whatsapp_import.ImportacionInvalida):
            whatsapp_import.importar_zip_whatsapp(falso_zip)
        self.assertEqual(self._contar_fotos(), 0)

    def test_imagen_invalida_se_descarta_sin_cambios(self):
        archivo_invalido = Path(self.temporal.name) / "imagen_invalida.zip"
        with zipfile.ZipFile(archivo_invalido, "w") as archivo:
            archivo.writestr("chat.txt", "exportación")
            archivo.writestr("falsa.jpg", b"contenido que no es una imagen")

        resultado = whatsapp_import.importar_zip_whatsapp(archivo_invalido)
        self.assertEqual(resultado.encontradas, 1)
        self.assertEqual(resultado.nuevas, 0)
        self.assertEqual(resultado.duplicadas, 0)
        self.assertEqual(resultado.descartadas, 1)
        self.assertEqual(resultado.errores, 0)
        self.assertEqual(self._contar_fotos(), 0)
        self.assertEqual(len(list(self.fotos_dir.iterdir())), 0)

    def test_imagen_demasiado_grande_se_descarta_sin_cambios(self):
        archivo_grande = Path(self.temporal.name) / "imagen_grande.zip"
        datos = b"\x00" * (whatsapp_import.MAX_BYTES_IMAGEN + 1)
        with zipfile.ZipFile(archivo_grande, "w", zipfile.ZIP_DEFLATED) as archivo:
            archivo.writestr("chat.txt", "exportación")
            archivo.writestr("demasiado_grande.jpg", datos)

        resultado = whatsapp_import.importar_zip_whatsapp(archivo_grande)
        self.assertEqual(resultado.encontradas, 1)
        self.assertEqual(resultado.nuevas, 0)
        self.assertEqual(resultado.descartadas, 1)
        self.assertEqual(self._contar_fotos(), 0)
        self.assertEqual(len(list(self.fotos_dir.iterdir())), 0)

    def test_zip_sin_imagenes_devuelve_ceros(self):
        solo_chat = Path(self.temporal.name) / "solo_chat.zip"
        with zipfile.ZipFile(solo_chat, "w") as archivo:
            archivo.writestr("chat.txt", "sin fotografías")
            archivo.writestr("audio.opus", b"OggS")
        resultado = whatsapp_import.importar_zip_whatsapp(solo_chat)
        self.assertEqual(resultado.encontradas, 0)
        self.assertEqual(resultado.nuevas, 0)
        self.assertEqual(self._contar_fotos(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
