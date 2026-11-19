# FichasPerros

Aplicación local para Windows destinada a importar fotografías de perros desde
exportaciones ZIP de WhatsApp y generar fichas imprimibles en PDF.

La aplicación permite gestionar fichas de perros, importar fotografías desde
WhatsApp, evitar duplicados mediante SHA-256, seleccionar imágenes y generar un
PDF de fichas imprimibles en A4.

## Requisitos

- Windows 10 u 11.
- Para el modo ventana: Microsoft Edge instalado (forma parte de Windows 10/11).
- Python 3.12 para ejecutar desde el código fuente.
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

## Aplicación de escritorio

Hacer doble clic en `FichasPerros.pyw`. Se inicia Flask en un puerto local
disponible y se abre una ventana propia con Microsoft Edge en modo aplicación,
sin barra de direcciones ni pestañas. Al cerrar la ventana, Flask se detiene.

El archivo `.pyw` usa `pythonw`, por lo que no muestra una consola. Durante el
desarrollo, si Windows lo abre con otro Python, el lanzador vuelve a ejecutarse
utilizando `.venv\Scripts\pythonw.exe`.

La ventana no usa Internet y no abre el navegador habitual.

Nota de compatibilidad: en el equipo de pruebas fue necesario que Edge
arrancase con el sandbox de Chromium desactivado para poder renderizar. La
ventana solo carga contenido local de `127.0.0.1` y no navega a sitios
externos.

## Distribución Windows

La distribución se genera con PyInstaller en modo **onedir**:

```text
dist\FichasPerros\
├── FichasPerros.exe
├── LEEME.txt
└── _internal\
```

El ejecutable no muestra consola y no necesita Python instalado. La carpeta
completa debe distribuirse junta; no hay que separar el `.exe` de `_internal`.

Para generar la distribución:

```powershell
.\build_windows.ps1
```

Si la política de ejecución de PowerShell bloquea el script:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

El script usa [FichasPerros.spec](FichasPerros.spec), copia el LEEME y crea
`dist\FichasPerros_Windows.zip`.

Se evaluó el modo onefile, pero en el equipo de pruebas no podía crear su
carpeta temporal y fallaba antes de arrancar. El modo onedir evita esa
extracción, arranca sin depender de `%TEMP%` y es más fiable para distribuir.
El coste es que la entrega es una carpeta, no un único archivo.

Requisitos para el voluntario:

- Windows 10 u 11.
- Microsoft Edge instalado.
- No se necesita Python ni WebView2 adicional.
- No se necesita conexión a Internet para usar la aplicación.

El ejecutable no está firmado digitalmente. Si Windows muestra una advertencia
de editor desconocido, hay que permitir su ejecución una vez.

## Uso

### Fichas

1. Abrir «Fichas» en la navegación superior.
2. Pulsar «Nueva ficha».
3. Rellenar los campos y seleccionar fotografías si se desean.
4. Guardar y consultar la ficha desde su pantalla de detalle.
5. Para modificarla, pulsar «Editar»; para eliminarla, «Eliminar» y confirmar.

La lista permite buscar por lugar, fecha, microchip, observaciones o número de
ficha.

### WhatsApp y PDF

1. Seleccionar un ZIP de exportación de WhatsApp.
2. Pulsar «Importar fotografías».
3. Consultar el resumen: encontradas, nuevas, duplicadas, descartadas y errores.
4. En la galería, seleccionar las fotografías que se quieran usar.
5. Pulsar «Continuar con las seleccionadas» para comprobar el resumen.
6. Pulsar «Generar PDF» y descargar el documento generado.

Las imágenes se guardan en `data/fotos` con nombres internos únicos. En SQLite
se conserva el nombre original del archivo y la ruta interna. Los archivos
originales no se modifican y las imágenes repetidas se detectan por hash,
aunque tengan nombres diferentes.

## Gestión de fichas

Cada ficha guarda lugar de recogida, fecha de recogida, número de microchip,
observaciones y sus fotografías. Se pueden crear fichas sin fotografías,
añadirlas después, asociar imágenes ya existentes en la biblioteca o subir
nuevas.

Al quitar una fotografía de una ficha, la imagen permanece en la biblioteca
general. Al eliminar una ficha se eliminan sus vínculos, pero no las
fotografías ni los PDF ya generados. Esto evita romper otras fichas y conserva
el historial de documentos.

## Galería y selección

La galería muestra una miniatura, el nombre original y una casilla por cada
fotografía. El contador, «Seleccionar todas» y «Deseleccionar todas» funcionan
en el navegador sin modificar la base de datos. El resumen muestra las
fotografías elegidas y permite generar el documento.

Las miniaturas se generan en memoria a partir de la imagen original. Se piden
por el identificador de SQLite y solo se sirven archivos situados dentro de
`data/fotos`.

## Generación de PDF

Cada fotografía seleccionada ocupa una ficha. El documento se compone en A4
vertical, con cuatro fichas iguales por página, márgenes de 12 mm y líneas
finas para recortar. Cada ficha tiene la fotografía en el tercio izquierdo y
los campos LUGAR DE RECOGIDA, FECHA DE RECOGIDA, Nº MICROCHIP y OBSERVACIONES
en el tercio derecho. Las filas que sobran en la última página quedan vacías.

Los documentos se guardan en `documentos/` con un nombre único. Las imágenes
originales de `data/fotos` no se modifican. El documento generado se descarga
desde la propia interfaz.

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
guardadas, conservación de hashes, rechazo de ZIP maliciosos, gestión de fichas
y ciclo de vida del servidor de escritorio. La generación de PDF se ha validado
con 1, 3, 4, 5, 6 y 10 fotografías.

Además se probó la distribución onedir generada: arranque sin consola, ventana
de Edge, navegación, creación de ficha, importación ZIP, PDF, ubicación de
datos en LocalAppData, cierre sin procesos residuales y reapertura con
persistencia.

## Datos y compatibilidad

La base de datos existente se conserva. Se añadieron las tablas `fichas` y
`ficha_fotos`; la tabla `fotos` y las fotografías ya importadas no se
modificaron. No se añadieron dependencias de Python.

Durante el desarrollo se mantienen las carpetas actuales del proyecto:
`data/` y `documentos/`.

Cuando la aplicación esté empaquetada, los datos persistentes se guardarán en:

```text
%LOCALAPPDATA%\FichasPerros\
├── fichas.db
├── fotos\
└── documentos\
```

Las rutas se calculan sin depender del directorio de ejecución ni de `_MEIPASS`.
El empaquetado definitivo con PyInstaller se realizará en una fase posterior.

## Estructura

```text
FichasPerros/
├── app.py                 # Aplicación Flask
├── database.py            # Conexión, esquema y rutas persistentes
├── desktop.py             # Servidor local + ventana de escritorio
├── FichasPerros.pyw       # Entrada de doble clic sin consola
├── FichasPerros.spec      # Configuración de PyInstaller (onedir)
├── build_windows.ps1      # Genera la distribución Windows
├── LEEME_DISTRIBUCION.txt # Instrucciones para el voluntario
├── ficha_service.py       # Creación, edición y borrado de fichas
├── whatsapp_import.py     # Importación segura de ZIP
├── pdf_generator.py       # Generación de fichas A4 en PDF
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── fichas_lista.html
│   ├── ficha_detalle.html
│   ├── ficha_formulario.html
│   └── ficha_eliminar.html
├── static/
│   ├── style.css
│   ├── gallery.js
│   └── ficha_form.js
├── data/
│   ├── fotos/             # Fotografías de la biblioteca
│   └── fichas.db          # Base de datos (se crea al arrancar)
├── documentos/            # PDF generados
└── pruebas/
    ├── exportacion_whatsapp_01.zip
    ├── exportacion_whatsapp_02.zip
    ├── test_importacion.py
    ├── test_fichas.py
    ├── test_desktop.py
    └── CREDITOS.md
```

La base de datos, las fotografías y los PDF generados son datos locales y no se
incluyen en Git. Las fotografías de los ZIP de prueba proceden de Wikimedia
Commons; sus autores y licencias se detallan en `pruebas/CREDITOS.md`.
