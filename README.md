# FichasPerros

Aplicación local para Windows destinada a importar fotografías de perros desde
exportaciones ZIP de WhatsApp y generar fichas imprimibles en PDF.

Esta primera fase deja preparado el proyecto, la base de datos y una pantalla
inicial. Todavía no se importan fotografías ni se generan PDF.

## Requisitos

- Windows 10 u 11.
- Python 3.12.
- Conexión a Internet únicamente para instalar las dependencias. La aplicación
  funciona después sin conexión.

## Instalación

Abrir PowerShell en la carpeta del proyecto y ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell impide activar el entorno, se puede usar directamente el Python
del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Abrir <http://127.0.0.1:5000> en el navegador. Para detener la aplicación,
pulsar `Ctrl+C` en la terminal.

## Estructura

```text
FichasPerros/
├── app.py                 # Aplicación Flask
├── database.py            # Conexión y esquema SQLite
├── whatsapp_import.py     # Reservado para la importación de ZIP
├── pdf_generator.py       # Reservado para la generación de PDF
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── static/
│   └── style.css
├── data/
│   ├── fotos/             # Fotografías importadas
│   └── fichas.db          # Base de datos (se crea al arrancar)
├── documentos/            # PDF generados
└── pruebas/
```

La base de datos y las fotografías son datos locales y no se incluyen en Git.
