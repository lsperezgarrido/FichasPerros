# FichasPerros — notas para colaboradores

Aplicación local para Windows destinada a gestionar fichas de perros e
imprimirlas en PDF. Funciona sin conexión y no requiere instalar Python si se
usa la distribución generada.

## Estado actual

- Aplicación de escritorio y distribución Windows terminadas y probadas.
- Los cambios de la última sesión están sin commitear: revisar con
  `git status` y `git diff` antes de hacer commit.
- Configuración: [FichasPerros.spec](FichasPerros.spec)
- Generación: [build_windows.ps1](build_windows.ps1)
- Distribución: `dist/FichasPerros_Windows.zip`
- Guía de instalación para un PC nuevo: sección «Poner en funcionamiento en un
  PC nuevo» de [README.md](README.md).
- Suite de pruebas: 36 pruebas, todas pasan.

## Requisitos para ejecutar desde código fuente

- Windows 10 u 11.
- Python 3.12.
- Microsoft Edge instalado para la ventana de escritorio.
- Dependencias en [`requirements.txt`](requirements.txt).

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

**Antes de reconstruir**, hacer copia de `dist\FichasPerros\datos` (si existe):
`build_windows.ps1` borra `dist\FichasPerros` por completo, incluidos los datos
de prueba o del usuario que estuvieran ahí. Después del build hay que restaurar
esa carpeta. En este equipo se ha usado `%TEMP%\opencode\fichas_datos_backup_*`.

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

Si `%LOCALAPPDATA%` no admite escritura (equipos con políticas restrictivas),
todo lo anterior se crea en `datos\` junto al ejecutable, incluido el perfil de
Edge. La comprobación se hace al importar `database.py`; en desarrollo no se
aplica.

El ZIP de distribución contiene solo el programa: los datos nunca van dentro.
En este equipo están en `dist\FichasPerros\datos\`, así que borrar esa carpeta
para volver a descomprimir el ZIP borra también fichas, fotos y PDF. Al
actualizar, extraer en otra carpeta y copiar `datos` desde la versión anterior.

Los datos de desarrollo se mantienen fuera de Git: `data/*.db`, `data/fotos/*` y `documentos/*`.

## Tecnología y decisiones

- Flask serviendo HTML/CSS/JS en `127.0.0.1`.
- Microsoft Edge en modo aplicación (`--app`) para la ventana de escritorio.
- PyWebView se probó y se descartó: fallaba al cargar pythonnet/.NET en este entorno.
- PyInstaller en modo `onedir`; `onefile` fallaba al crear su carpeta temporal.
- `--no-sandbox` sigue siendo necesario en el lanzador de Edge: al probar a
  quitarlo, Edge arrancaba pero no cargaba la página local. La ventana solo
  carga contenido local y Edge muestra una advertencia por ese modificador.
- La importación de un ZIP crea una ficha en blanco por foto nueva y las
  agrupa en `hojas` de `POR_HOJA` (=4) perros, con un PDF por hoja. La
  deduplicación es por hash SHA-256 de la imagen. La unidad visible en
  «Fichas» es la hoja, con estado generada/pendiente; los perros se editan
  desde el detalle de la hoja. `hoja_service.py` concentra esa lógica. La
  plantilla del PDF no se ha tocado: los campos siguen saliendo vacíos.
- `app.py` fija `tempfile.tempdir` a la carpeta de datos: en este equipo
  `%TEMP%` no es escribible para ejecutables sin firma y Werkzeug fallaba al
  recibir el ZIP con un 500. No quitar esa línea.
- Al migrar una base antigua se agrupan las fichas por id en hojas de cuatro y
  se asocian los PDF existentes por orden de nombre; se marca en `metadata`
  para no repetir la migración.

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
- `hoja_service.py` — Hojas de cuatro perros, generación y borrado de PDF.
- `whatsapp_import.py` — Importación segura de ZIP de WhatsApp.
- `pdf_generator.py` — Generación de fichas A4 en PDF.
- `FichasPerros.spec` / `build_windows.ps1` — Empaquetado Windows.
- `pruebas/` — Suite de pruebas automatizadas.
