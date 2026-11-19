# FichasPerros

Aplicación local para Windows destinada a importar fotografías de perros desde
exportaciones ZIP de WhatsApp y generar fichas imprimibles en PDF.

Actualmente la aplicación permite importar fotografías y evita duplicados
mediante su hash SHA-256. La generación de PDF se añadirá en una fase posterior.

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

## Uso

1. Seleccionar un ZIP de exportación de WhatsApp.
2. Pulsar «Importar fotografías».
3. Consultar el resumen: encontradas, nuevas, duplicadas, descartadas y errores.

Las imágenes se guardan en `data/fotos` con nombres internos únicos. En SQLite
se conserva el nombre original del archivo del ZIP y la ruta interna. Los
archivos originales no se modifican y las imágenes repetidas se detectan por
hash, aunque tengan nombres diferentes.

## Seguridad de la importación

- Los archivos se leen del ZIP, nunca se extraen ni se ejecutan.
- Se rechazan nombres con rutas peligrosas (ZIP Slip).
- Se validan las imágenes con Pillow antes de guardarlas.
- Solo se admiten JPG, JPEG, PNG y WEBP.
- Límites: 200 MB por ZIP, 500 MB descomprimidos, 20 MB por imagen y 2000
  entradas.
- Una importación inválida no modifica la base de datos.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

Incluye comprobaciones de importación, duplicados, apertura de las imágenes
guardadas, conservación de hashes y rechazo de ZIP maliciosos.

## Estructura

```text
FichasPerros/
├── app.py                 # Aplicación Flask
├── database.py            # Conexión y esquema SQLite
├── whatsapp_import.py     # Importación segura de ZIP
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
    ├── exportacion_whatsapp_01.zip
    ├── exportacion_whatsapp_02.zip
    ├── test_importacion.py
    └── CREDITOS.md
```

La base de datos y las fotografías son datos locales y no se incluyen en Git.
Las fotografías de los ZIP de prueba proceden de Wikimedia Commons; sus
autores y licencias se detallan en `pruebas/CREDITOS.md`.
