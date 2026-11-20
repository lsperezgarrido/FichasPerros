"""Pruebas del modelo de hojas de cuatro fichas."""

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
import hoja_service  # noqa: E402


class HojasTests(unittest.TestCase):
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

    def _insertar_fotos(self, cantidad):
        conexion = database.get_connection()
        ids = []
        try:
            with conexion:
                for indice in range(cantidad):
                    cursor = conexion.execute(
                        "INSERT INTO fotos (nombre_archivo, ruta, hash_sha256) "
                        "VALUES (?, ?, ?)",
                        (f"f{indice}.jpg", f"fotos/f{indice}.jpg", f"hash-{indice}"),
                    )
                    ids.append(cursor.lastrowid)
        finally:
            conexion.close()
        return ids

    def test_importacion_agrupa_en_hojas_de_cuatro(self):
        ids = self._insertar_fotos(7)
        hojas = hoja_service.registrar_importacion(ids)

        self.assertEqual(len(hojas), 2)
        self.assertEqual(
            [len(database.listar_perros_hoja(h)) for h in hojas], [4, 3]
        )
        self.assertTrue(all(database.obtener_hoja(h)["nombre_pdf"] is None for h in hojas))

    def test_migracion_agrupa_fichas_y_asocia_pdfs(self):
        for _ in range(8):
            conexion = database.get_connection()
            with conexion:
                conexion.execute(
                    "INSERT INTO fichas (lugar_recogida) VALUES ('Refugio')"
                )
            conexion.close()
        database.DOCUMENTOS_DIR.mkdir(parents=True, exist_ok=True)
        nombres = ["fichas_20240101_000000_aaaaaaaa.pdf", "fichas_20240201_000000_bbbbbbbb.pdf"]
        for nombre in nombres:
            (database.DOCUMENTOS_DIR / nombre).write_bytes(b"%PDF-1.4\n")

        conexion = database.get_connection()
        with conexion:
            conexion.execute("DELETE FROM metadata WHERE clave = 'hojas_v1'")
        conexion.close()
        database.init_db()

        hojas = database.listar_hojas()
        self.assertEqual(len(hojas), 2)
        self.assertEqual([h["num_perros"] for h in hojas], [4, 4])
        self.assertEqual(
            sorted(h["nombre_pdf"] for h in hojas), sorted(nombres)
        )

    def test_eliminar_hoja_conserva_los_perros_y_borra_el_pdf(self):
        hoja_id = hoja_service.registrar_importacion(self._insertar_fotos(4))[0]
        database.DOCUMENTOS_DIR.mkdir(parents=True, exist_ok=True)
        ruta = database.DOCUMENTOS_DIR / "fichas_prueba.pdf"
        ruta.write_bytes(b"%PDF-1.4\n")
        database.actualizar_pdf_hoja(hoja_id, ruta.name, "2024-01-01 00:00:00")

        self.assertTrue(hoja_service.eliminar_hoja(hoja_id))
        self.assertEqual(len(database.listar_fichas()), 4)
        self.assertEqual(database.listar_hojas(), [])
        self.assertFalse(ruta.exists())

    def test_eliminar_perro_deja_su_hoja_pendiente(self):
        hoja_id = hoja_service.registrar_importacion(self._insertar_fotos(4))[0]
        database.actualizar_pdf_hoja(hoja_id, "fichas_prueba.pdf", "2024-01-01 00:00:00")
        ficha_id = database.listar_perros_hoja(hoja_id)[0]["id"]

        hoja_service.invalidar_pdf_hoja(ficha_id)

        self.assertIsNone(database.obtener_hoja(hoja_id)["nombre_pdf"])

    def test_rutas_de_hojas(self):
        hoja_id = hoja_service.registrar_importacion(self._insertar_fotos(4))[0]
        with app.app.test_client() as cliente:
            lista = cliente.get("/fichas")
            detalle = cliente.get(f"/fichas/hoja/{hoja_id}")
            confirmacion = cliente.get(f"/fichas/hoja/{hoja_id}/eliminar")
            borrado = cliente.post(f"/fichas/hoja/{hoja_id}/eliminar")

        self.assertEqual(lista.status_code, 200)
        self.assertIn(b"Hoja #" + str(hoja_id).encode(), lista.data)
        self.assertEqual(detalle.status_code, 200)
        self.assertIn(b"Pendiente de generar", detalle.data)
        self.assertEqual(confirmacion.status_code, 200)
        self.assertEqual(borrado.status_code, 302)
        self.assertEqual(database.listar_hojas(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
