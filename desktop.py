"""Lanzador de escritorio de FichasPerros basado en el modo aplicación de Edge."""

from __future__ import annotations

import ctypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

from werkzeug.serving import make_server

import database

HOST = "127.0.0.1"
ANCHO_VENTANA = "1280,900"
ESPERA_ARRANQUE_EDGE = 2.0
CODIGO_PERFIL_BLOQUEADO = 21

PROYECTO = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    # Mismo directorio de datos que la base de datos: si %LOCALAPPDATA% no es
    # escribible, el perfil de Edge también se crea junto al ejecutable.
    PERFIL_EDGE = database.BASE_DIR / "edge-profile"
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
    # Importación diferida: así los errores de arranque de la aplicación
    # (por ejemplo, una base de datos no escribible) se pueden mostrar en un
    # cuadro de diálogo en lugar de cerrar el ejecutable sin explicación.
    import app

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


def _argumentos_edge(edge: Path, url: str, perfil: Path) -> list[str]:
    return [
        str(edge),
        f"--app={url}",
        f"--user-data-dir={perfil}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-extensions",
        "--disable-sync",
        f"--window-size={ANCHO_VENTANA}",
        # Necesario en este Windows: sin él, Edge no consigue cargar la página
        # cuando lo lanza la aplicación y muestra una pantalla de error.
        "--no-sandbox",
    ]


def _lanzar_edge(
    edge: Path,
    url: str,
    perfil: Path,
) -> tuple[subprocess.Popen | None, int | None]:
    """Lanza Edge y comprueba que sigue vivo tras el arranque.

    Devuelve ``(proceso, None)`` si la ventana se mantiene abierta, o
    ``(None, codigo)`` si Edge se cerró. Edge devuelve el código 21 cuando no
    puede crear el archivo de bloqueo de su perfil.
    """
    proceso = subprocess.Popen(
        _argumentos_edge(edge, url, perfil),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    limite = time.monotonic() + ESPERA_ARRANQUE_EDGE
    while time.monotonic() < limite:
        codigo = proceso.poll()
        if codigo is not None:
            return None, codigo
        time.sleep(0.1)
    return proceso, None


def _apartar_perfil(perfil: Path) -> Path:
    """Renombra un perfil de Edge inservible y devuelve uno nuevo.

    El perfil anterior se conserva como copia de seguridad; no se borra nada.
    Si no se puede renombrar (porque sigue en uso), se reintenta con el mismo.
    """
    if perfil.exists():
        marca = time.strftime("%Y%m%d_%H%M%S")
        respaldo = perfil.with_name(f"{perfil.name}-bak-{marca}")
        contador = 1
        while respaldo.exists():
            respaldo = perfil.with_name(f"{perfil.name}-bak-{marca}-{contador}")
            contador += 1
        try:
            perfil.rename(respaldo)
        except OSError:
            return perfil

    perfil.mkdir(parents=True, exist_ok=True)
    return perfil


def _mostrar_error(mensaje: str) -> None:
    """Muestra un aviso visible aunque el ejecutable no tenga consola."""
    try:
        ctypes.windll.user32.MessageBoxW(0, mensaje, "FichasPerros", 0x10)
    except Exception:
        print(mensaje, file=sys.stderr)


def main() -> None:
    edge = buscar_edge()
    if edge is None:
        raise RuntimeError(
            "No se encontró Microsoft Edge. Es necesario para abrir la ventana "
            "de FichasPerros en este equipo."
        )

    servidor, hilo = iniciar_servidor()
    url = f"http://{HOST}:{servidor.server_port}/"
    perfil = PERFIL_EDGE
    proceso = None
    codigo = None

    try:
        perfil.mkdir(parents=True, exist_ok=True)
        proceso, codigo = _lanzar_edge(edge, url, perfil)

        if proceso is None and codigo == CODIGO_PERFIL_BLOQUEADO:
            # El perfil no se puede bloquear (suele estar dañado tras un cierre
            # abrupto). Se aparta y se prueba una sola vez con uno nuevo.
            perfil = _apartar_perfil(perfil)
            proceso, codigo = _lanzar_edge(edge, url, perfil)

        if proceso is None:
            if codigo in (0, 1):
                # Otra instancia de Edge ya está mostrando la ventana.
                return
            raise RuntimeError(
                "Microsoft Edge se cerró al abrir la ventana de FichasPerros "
                f"(código {codigo}). Comprueba que Edge funciona correctamente "
                "y vuelve a intentarlo."
            )

        try:
            proceso.wait()
        finally:
            if proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proceso.kill()
    finally:
        detener_servidor(servidor, hilo)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _mostrar_error(
            "No se pudo iniciar FichasPerros.\n\n"
            + traceback.format_exc(limit=6)
        )
        sys.exit(1)
