"""Pruebas del lanzador de escritorio y de las rutas persistentes."""

from __future__ import annotations

import socket
import sys
import unittest
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import database  # noqa: E402
import desktop  # noqa: E402


class RutasPersistentesTests(unittest.TestCase):
    def test_directorios_de_desarrollo(self):
        proyecto = Path(r"C:\proyecto")
        base, datos, documentos = database._resolver_directorios(
            False,
            r"C:\Users\ejemplo\AppData\Local",
            proyecto,
        )
        self.assertEqual(base, proyecto)
        self.assertEqual(datos, proyecto / "data")
        self.assertEqual(documentos, proyecto / "documentos")

    def test_directorios_de_ejecutable(self):
        proyecto = Path(r"C:\proyecto")
        local = Path(r"C:\Users\ejemplo\AppData\Local")
        base, datos, documentos = database._resolver_directorios(
            True,
            str(local),
            proyecto,
        )
        esperado = local / "FichasPerros"
        self.assertEqual(base, esperado)
        self.assertEqual(datos, esperado)
        self.assertEqual(documentos, esperado / "documentos")

    def test_rutas_actuales_de_desarrollo(self):
        self.assertEqual(database.DATA_DIR, BASE_DIR / "data")
        self.assertEqual(database.DOCUMENTOS_DIR, BASE_DIR / "documentos")


class LanzadorEscritorioTests(unittest.TestCase):
    def test_edge_disponible(self):
        edge = desktop.buscar_edge()
        self.assertIsNotNone(edge)
        self.assertTrue(edge.is_file())

    def test_servidor_dinamico_y_cierre(self):
        servidor, hilo = desktop.iniciar_servidor()
        puerto = servidor.server_port
        try:
            self.assertEqual(servidor.server_address[0], "127.0.0.1")
            self.assertGreater(puerto, 0)
            with urllib.request.urlopen(
                f"http://127.0.0.1:{puerto}/", timeout=10
            ) as respuesta:
                html = respuesta.read().decode("utf-8")
                self.assertEqual(respuesta.status, 200)
                self.assertIn("Fichas de perros", html)
        finally:
            desktop.detener_servidor(servidor, hilo)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.settimeout(1)
            self.assertNotEqual(
                cliente.connect_ex(("127.0.0.1", puerto)),
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
