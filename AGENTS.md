# FichasPerros — notas para colaboradores

Aplicación local para Windows destinada a gestionar fichas de perros e
imprimirlas en PDF. Funciona sin conexión y no requiere instalar Python si se
usa la distribución generada.

## Estado actual

- Fase 5 completada: aplicación de escritorio (5B) y distribución Windows (5C).
- Último commit: `ecc353ebcdbe016f9f442d8b44a31b9139efedeb`
- Configuración: [FichasPerros.spec](FichasPerros/FichasPerros.spec)
- Generación: [build_windows.ps1](FichasPerros/build_windows.ps1)
- Distribución: `FichasPerros/dist/FichasPerros_Windows.zip`

## Requisitos para ejecutar desde código fuente

- Windows 10 u 11.
- Python 3.12.
- Microsoft Edge instalado para la ventana de escritorio.
- Dependenzas en [`requirements.txt`](FichasPerros/requirements.txt).

## Comandos comunes

```powershell
# Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Ejecutar en desarrollo con navegador normal
.\.venv\Scripts\Activate.ps1
python app.py
# Abrir http://127.0.0.1:5000 en el navegador

# Ejecutar como aplicación de escritorio (sin consola)
.\.venv\Scripts\Activate.ps1
pythonw FichasPerros.pyw
# o hacer doble clic directamente en FichasPerros.pyw

# Ejecutar pruebas
.\.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

## Generar la distribución Windows

```powershell
.\build_windows.ps1
# o, si PowerShell bloquea scripts:
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Resultados:

- `dist/FichasPerros/FichasPerros.exe`
- `dist/FichasPerros/_internal/`
- `dist/FichasPerros/LEEME.txt`
- `dist/FichasPerros_Windows.zip`

No mover únicamente el `.exe`: la carpeta completa debe distribuirse junta.

## Datos

### Durante el desarrollo
- `data/fotos/`
- `data/fichas.db`
- `documentos/`

### En la versión empaquetada
- `%LOCALAPPDATA%\FichasPerros\fichas.db`
- `%LOCALAPPDATA%\FichasPerros\fotos\`
- `%LOCALAPPDATA%\FichasPerros\documentos\`
- `%LOCALAPPDATA%\FichasPerros\edge-profile\` (perfil interno de Edge)

Los datos de desarrollo se mantienen fuera de Git: `data/*.db`, `data/fotos/*` y `documentos/*`.

## Tecnología y decisiones

- Flask serviendo HTML/CSS/JS en `127.0.0.1`.
- Microsoft Edge en modo aplicación (`--app`) para la ventana de escritorio.
- PyWebView se probó y se descartó: fallaba al cargar pythonnet/.NET en este entorno.
- PyInstaller en modo `onedir`; `onefile` fallaba al crear su carpeta temporal.
- `--no-sandbox` está presente en el lanzador de Edge para evitar fallos de
  renderizado en este Windows. La ventana solo carga contenido local.

## Convenciones de commit

- No modificar el diseño de la interfaz, la plantilla PDF ni rehacer Flask.
- No añadir dependencias salvo las estrictamente necesarias.
- No mover datos de desarrollo ni sobrescribir datos existentes de forma
  destructiva.
- Revisar los cambios antes de commitear.

## Estructura del proyecto

- `app.py` — Aplicación Flask.
- `database.py` — SQLite, esquema y rutas persistentes.
- `desktop.py` — Servidor local + ventana de escritorio.
- `FichasPerros.pyw` — Entrada de doble clic sin consola.
- `ficha_service.py` — Creación, edición y borrado de fichas.
- `whatsapp_import.py` — Importación segura de ZIP de WhatsApp.
- `pdf_generator.py` — Generación de fichas A4 en PDF.
- `FichasPerros.spec` / `build_windows.ps1` — Empaquetado Windows.
- `pruebas/` — Suite de pruebas automatizadas.
