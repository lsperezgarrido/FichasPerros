"""Pruebas de gestión de fichas y de sus fotografías."""

from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from werkzeug.datastructures import FileStorage

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import database  # noqa: E402
import ficha_service  # noqa: E402


class GestionFichasTests(unittest.TestCase):
    """Cubre creación, consulta, edición, fotografías y borrado."""

    def setUp(self):
        self._data_original = database.DATA_DIR
        self._db_original = database.DB_PATH
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.addCleanup(self._restaurar_database)

        database.DATA_DIR = Path(self.temporal.name) / "data"
        database.DB_PATH = database.DATA_DIR / "fichas.db"
        database.init_db()
        self.fotos_dir = database.DATA_DIR / "fotos"

    def _restaurar_database(self):
        database.DATA_DIR = self._data_original
        database.DB_PATH = self._db_original

    def _imagen(self, nombre, color, formato="JPEG"):
        imagen = Image.new("RGB", (240, 180), color)
        buffer = io.BytesIO()
        imagen.save(buffer, formato)
        buffer.seek(0)
        content_type = "image/jpeg" if formato == "JPEG" else "image/png"
        return FileStorage(stream=buffer, filename=nombre, content_type=content_type)

    def _ficha(self, **cambios):
        datos = {
            "lugar_recogida": "",
            "fecha_recogida": "",
            "numero_microchip": "",
            "observaciones": "",
        }
        datos.update(cambios)
        return datos

    def _filas(self, tabla):
        conexion = database.get_connection()
        try:
            return conexion.execute(f"SELECT * FROM {tabla}").fetchall()
        finally:
            conexion.close()

    def test_crear_ficha_sin_fotografias(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Refugio norte"),
            [],
        )
        ficha = database.obtener_ficha(ficha_id)
        self.assertIsNotNone(ficha)
        self.assertEqual(ficha["lugar_recogida"], "Refugio norte")
        self.assertEqual(database.listar_fotos_ficha(ficha_id), [])
        self.assertEqual(len(self._filas("fichas")), 1)

    def test_crear_ficha_con_varias_fotografias(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(
                lugar_recogida="Parque",
                fecha_recogida="2026-01-15",
                numero_microchip="CHIP-001",
                observaciones="Muy sociable",
            ),
            [
                self._imagen("primera.jpg", "red"),
                self._imagen("segunda.png", "blue", "PNG"),
            ],
        )
        fotos = database.listar_fotos_ficha(ficha_id)
        self.assertEqual(len(fotos), 2)
        self.assertEqual([foto["nombre_archivo"] for foto in fotos], ["primera.jpg", "segunda.png"])
        for foto in fotos:
            ruta = database.DATA_DIR / foto["ruta"]
            self.assertTrue(ruta.is_file())
            with Image.open(ruta) as imagen:
                imagen.load()
        self.assertEqual(len(self._filas("fotos")), 2)
        self.assertEqual(len(self._filas("ficha_fotos")), 2)

    def test_consultar_y_buscar_fichas(self):
        primera = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Alameda", numero_microchip="CHIP-AAA"),
            [],
        )
        segunda = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Estación", observaciones="Perra mayor"),
            [],
        )
        self.assertEqual(database.obtener_ficha(primera)["lugar_recogida"], "Alameda")
        self.assertEqual(database.obtener_ficha(segunda)["lugar_recogida"], "Estación")

        por_microchip = database.listar_fichas("CHIP-AAA")
        self.assertEqual([ficha["id"] for ficha in por_microchip], [primera])
        por_observaciones = database.listar_fichas("mayor")
        self.assertEqual([ficha["id"] for ficha in por_observaciones], [segunda])
        por_id = database.listar_fichas(str(segunda))
        self.assertEqual([ficha["id"] for ficha in por_id], [segunda])
        self.assertEqual(database.listar_fichas("no existe"), [])

        con_fecha = ficha_service.crear_ficha(
            self._ficha(fecha_recogida="2026-04-05"),
            [],
        )
        por_fecha = database.listar_fichas("05/04/2026")
        self.assertEqual([ficha["id"] for ficha in por_fecha], [con_fecha])

    def test_actualizar_datos(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Antiguo"),
            [],
        )
        ficha_service.actualizar_ficha(
            ficha_id,
            self._ficha(
                lugar_recogida="Nuevo lugar",
                fecha_recogida="2026-02-20",
                numero_microchip="CHIP-NUEVO",
                observaciones="Actualizada",
            ),
            [],
            set(),
        )
        ficha = database.obtener_ficha(ficha_id)
        self.assertEqual(ficha["lugar_recogida"], "Nuevo lugar")
        self.assertEqual(ficha["fecha_recogida"], "2026-02-20")
        self.assertEqual(ficha["numero_microchip"], "CHIP-NUEVO")
        self.assertEqual(ficha["observaciones"], "Actualizada")

    def test_agregar_y_quitar_fotografias(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Ficha con fotos"),
            [self._imagen("original.jpg", "green")],
        )
        foto_original = database.listar_fotos_ficha(ficha_id)[0]
        archivo_original = database.DATA_DIR / foto_original["ruta"]

        ficha_service.actualizar_ficha(
            ficha_id,
            self._ficha(lugar_recogida="Ficha con fotos"),
            [self._imagen("nueva.jpg", "yellow")],
            {foto_original["id"]},
        )
        fotos = database.listar_fotos_ficha(ficha_id)
        self.assertEqual([foto["nombre_archivo"] for foto in fotos], ["nueva.jpg"])
        self.assertTrue(archivo_original.is_file())
        self.assertEqual(len(self._filas("fotos")), 2)
        self.assertEqual(len(self._filas("ficha_fotos")), 1)

    def test_eliminar_ficha_no_borra_fotografias_ni_otras_fichas(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Se elimina"),
            [self._imagen("foto.jpg", "purple")],
        )
        otra_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Se conserva"),
            [self._imagen("otra.jpg", "orange")],
        )
        foto = database.listar_fotos_ficha(ficha_id)[0]
        archivo = database.DATA_DIR / foto["ruta"]

        self.assertTrue(ficha_service.eliminar_ficha(ficha_id))
        self.assertIsNone(database.obtener_ficha(ficha_id))
        self.assertEqual(database.listar_fotos_ficha(ficha_id), [])
        self.assertIsNotNone(database.obtener_ficha(otra_id))
        self.assertEqual(len(database.listar_fotos_ficha(otra_id)), 1)
        self.assertEqual(len(self._filas("fotos")), 2)
        self.assertTrue(archivo.is_file())

    def test_fotografia_duplicada_se_reutiliza(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(),
            [
                self._imagen("a.jpg", "gray"),
                self._imagen("b.jpg", "gray"),
            ],
        )
        self.assertEqual(len(database.listar_fotos_ficha(ficha_id)), 1)
        self.assertEqual(len(self._filas("fotos")), 1)
        self.assertEqual(len(self._filas("ficha_fotos")), 1)

    def test_datos_y_archivos_invalidos_no_crean_ficha(self):
        with self.assertRaises(ficha_service.ErrorFicha):
            ficha_service.crear_ficha(self._ficha(fecha_recogida="2026-13-40"), [])
        with self.assertRaises(ficha_service.ErrorFicha):
            ficha_service.crear_ficha(
                self._ficha(),
                [FileStorage(stream=io.BytesIO(b"no es imagen"), filename="falsa.jpg")],
            )
        with self.assertRaises(ficha_service.ErrorFicha):
            ficha_service.crear_ficha(
                self._ficha(),
                [FileStorage(stream=io.BytesIO(b"GIF89a"), filename="foto.gif")],
            )
        self.assertEqual(self._filas("fichas"), [])
        self.assertEqual(self._filas("fotos"), [])
        self.assertFalse(self.fotos_dir.exists() and any(self.fotos_dir.iterdir()))

    def test_init_db_conserva_fichas_y_fotografias(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(lugar_recogida="Persistente"),
            [self._imagen("persistente.jpg", "silver")],
        )
        database.init_db()
        self.assertIsNotNone(database.obtener_ficha(ficha_id))
        self.assertEqual(len(database.listar_fotos_ficha(ficha_id)), 1)

    def test_hash_guardado_coincide_con_el_archivo(self):
        ficha_id = ficha_service.crear_ficha(
            self._ficha(),
            [self._imagen("hash.jpg", "black")],
        )
        foto = database.listar_fotos_ficha(ficha_id)[0]
        ruta = database.DATA_DIR / foto["ruta"]
        conexion = database.get_connection()
        try:
            hash_db = conexion.execute(
                "SELECT hash_sha256 FROM fotos WHERE id = ?", (foto["id"],)
            ).fetchone()[0]
        finally:
            conexion.close()
        self.assertEqual(hashlib.sha256(ruta.read_bytes()).hexdigest(), hash_db)


if __name__ == "__main__":
    unittest.main(verbosity=2)
