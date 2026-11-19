"""Entrada de escritorio sin consola para Windows."""

import ctypes
import subprocess
import sys
import traceback
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent
PYTHONW_VENV = PROYECTO / ".venv" / "Scripts" / "pythonw.exe"

if PYTHONW_VENV.is_file():
    actual = Path(sys.executable).resolve()
    esperado = PYTHONW_VENV.resolve()
    if actual != esperado:
        subprocess.Popen(
            [str(esperado), str(Path(__file__).resolve())],
            cwd=str(PROYECTO),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        raise SystemExit(0)

try:
    from desktop import main

    main()
except Exception:
    detalle = traceback.format_exc(limit=4)
    ctypes.windll.user32.MessageBoxW(
        0,
        "No se pudo iniciar FichasPerros.\n\n" + detalle,
        "FichasPerros",
        0x10,
    )
