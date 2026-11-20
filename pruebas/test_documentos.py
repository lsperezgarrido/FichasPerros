"""Pruebas de entrega de los PDF generados al navegador."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app  # noqa: E402
import database  # noqa: E402


class EntregaDocumentosTests(unittest.TestCase):
    def test_documento_se_entrega_en_linea(self):
        with tempfile.TemporaryDirectory() as temporal:
            original = database.DOCUMENTOS_DIR
            database.DOCUMENTOS_DIR = Path(temporal)
            try:
                (Path(temporal) / "fichas_prueba.pdf").write_bytes(b"%PDF-1.4\n")
                with app.app.test_client() as cliente:
                    respuesta = cliente.get("/documentos/fichas_prueba.pdf")
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.mimetype, "application/pdf")
                self.assertIn(
                    "inline",
                    respuesta.headers.get("Content-Disposition", ""),
                )
                respuesta.get_data()
                respuesta.close()
            finally:
                database.DOCUMENTOS_DIR = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
