"""Prueba del flujo completo: importar, crear fichas y generar el PDF."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app  # noqa: E402
import database  # noqa: E402

ZIP = BASE_DIR / "pruebas" / "exportacion_whatsapp_01.zip"


class FlujoImportacionTests(unittest.TestCase):
    def setUp(self):
        self._originales = (
            database.DATA_DIR,
            database.DB_PATH,
            database.DOCUMENTOS_DIR,
        )
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.addCleanup(self._restaurar)

        base = Path(self.temporal.name)
        database.DATA_DIR = base / "data"
        database.DB_PATH = database.DATA_DIR / "fichas.db"
        database.DOCUMENTOS_DIR = base / "documentos"
        database.init_db()

    def _restaurar(self):
        (
            database.DATA_DIR,
            database.DB_PATH,
            database.DOCUMENTOS_DIR,
        ) = self._originales

    def _importar(self, cliente):
        return cliente.post(
            "/importar",
            data={
                "archivo_zip": (
                    io.BytesIO(ZIP.read_bytes()),
                    "exportacion.zip",
                )
            },
            content_type="multipart/form-data",
        )

    def _pdfs(self):
        return list(database.DOCUMENTOS_DIR.glob("fichas_*.pdf"))

    def test_importar_crea_fichas_y_pdf_y_reimportar_no_duplica(self):
        with app.app.test_client() as cliente:
            primera = self._importar(cliente)

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(len(database.listar_fichas()), 7)
        self.assertEqual(len(database.listar_hojas()), 2)
        self.assertEqual(len(self._pdfs()), 2)
        self.assertIn(b"PDF generado con 7", primera.data)
        self.assertIn(b"Ver PDF", primera.data)

        with app.app.test_client() as cliente:
            segunda = self._importar(cliente)

        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(len(database.listar_fichas()), 7)
        self.assertEqual(len(database.listar_hojas()), 2)
        self.assertEqual(len(self._pdfs()), 2)
        self.assertNotIn(b"PDF generado con", segunda.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
