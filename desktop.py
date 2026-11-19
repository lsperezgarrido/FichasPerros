"""Lanzador de escritorio de FichasPerros basado en el modo aplicación de Edge."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from werkzeug.serving import make_server

import app

HOST = "127.0.0.1"
ANCHO_VENTANA = "1280,900"
PROYECTO = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    PERFIL_EDGE = (
        Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        / "FichasPerros"
        / "edge-profile"
    )
else:
    PERFIL_EDGE = PROYECTO / ".edge-profile"


def buscar_edge() -> Path | None:
    """Localiza Microsoft Edge en las ubicaciones habituales de Windows."""
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if not base:
            continue
        candidato = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if candidato.is_file():
            return candidato

    candidatos_edgecore = []
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if not base:
            continue
        edge_core = Path(base) / "Microsoft" / "EdgeCore"
        if edge_core.is_dir():
            candidatos_edgecore.extend(edge_core.glob("*/msedge.exe"))

    def clave_version(ruta: Path):
        try:
            return tuple(int(parte) for parte in ruta.parent.name.split("."))
        except ValueError:
            return (0,)

    for candidato in sorted(candidatos_edgecore, key=clave_version, reverse=True):
        if candidato.is_file():
            return candidato

    encontrado = shutil.which("msedge.exe")
    return Path(encontrado) if encontrado else None


def iniciar_servidor():
    """Inicia Flask en un puerto local libre y espera a que responda."""
    servidor = make_server(HOST, 0, app.app, threaded=True)
    hilo = threading.Thread(
        target=servidor.serve_forever,
        name="fichas-flask",
        daemon=True,
    )
    hilo.start()
    try:
        _esperar_servidor(servidor.server_port)
    except Exception:
        servidor.shutdown()
        hilo.join(timeout=5)
        servidor.server_close()
        raise
    return servidor, hilo


def detener_servidor(servidor, hilo) -> None:
    """Detiene el servidor y libera el puerto."""
    servidor.shutdown()
    hilo.join(timeout=5)
    servidor.server_close()


def _esperar_servidor(puerto: int, timeout: float = 5.0) -> None:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.settimeout(0.5)
            if cliente.connect_ex((HOST, puerto)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError("El servidor local no ha arrancado a tiempo.")


def main() -> None:
    edge = buscar_edge()
    if edge is None:
        raise RuntimeError(
            "No se encontró Microsoft Edge. Es necesario para abrir la ventana "
            "de FichasPerros en este equipo."
        )

    perfil = PERFIL_EDGE
    perfil.mkdir(parents=True, exist_ok=True)
    servidor, hilo = iniciar_servidor()
    proceso = None
    url = f"http://{HOST}:{servidor.server_port}/"
    argumentos = [
        str(edge),
        f"--app={url}",
        f"--user-data-dir={perfil}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-extensions",
        "--disable-sync",
        f"--window-size={ANCHO_VENTANA}",
        # Contenido exclusivamente local; necesario en entornos Windows
        # restringidos donde el renderer de Edge no arranca con sandbox.
        "--no-sandbox",
    ]

    try:
        proceso = subprocess.Popen(
            argumentos,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        proceso.wait()
    finally:
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
        detener_servidor(servidor, hilo)


if __name__ == "__main__":
    main()
