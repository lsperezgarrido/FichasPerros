# FichasPerros

Aplicación local para Windows destinada a importar fotografías de perros desde
exportaciones ZIP de WhatsApp y generar **hojas imprimibles en A4 con cuatro
fichas por hoja**.

Evita duplicados por SHA-256, lleva el control de qué hojas tienen PDF generado
y cuáles están pendientes, y funciona sin conexión.

## Poner en funcionamiento en un PC nuevo

No hace falta instalar Python ni tener conexión a Internet. Solo se necesita
Windows 10 u 11 y Microsoft Edge (viene instalado con Windows).

1. Copia `dist\FichasPerros_Windows.zip` al PC nuevo.
2. Haz clic derecho sobre el ZIP → **Extraer todo**. Se crea una carpeta
   `FichasPerros` con tres elementos: `FichasPerros.exe`, la carpeta `_internal`
   y `LEEME.txt`.
   - Si al extraer aparece una carpeta `FichasPerros` **dentro de otra**, has
     extraído dentro de una carpeta ya existente. Extrae el ZIP en una carpeta
     vacía y entra en la `FichasPerros` resultante.
3. Entra en esa carpeta y haz **doble clic en `FichasPerros.exe`**.
4. Si Windows muestra la primera vez un aviso de «editor desconocido», pulsa
   **Más información** → **Ejecutar de todas formas**. El ejecutable no está
   firmado digitalmente; es habitual.
5. Si aparece una franja amarilla de Edge sobre `--no-sandbox`, ciérrala con la
   **X**. Es una advertencia esperada en este equipo; la ventana solo carga
   contenido local de `127.0.0.1`.
6. Espera unos segundos: se abre una ventana propia llamada «Fichas de perros»,
   sin barra de direcciones ni pestañas.
7. En la pantalla «Inicio», selecciona el ZIP de WhatsApp y pulsa
   **Importar fotografías**. Las fotos nuevas se agrupan en hojas de cuatro y
   se genera su PDF automáticamente.
8. En «Fichas» verás una entrada por hoja con su estado (generada o pendiente).
   Abre una hoja para editar los datos de cada perro o para ver/generar su PDF.
9. Para cerrar, cierra la ventana. El servidor local se detiene solo.

**No separes `FichasPerros.exe` de la carpeta `_internal`**: deben viajar
juntos. Puedes mover o renombrar la carpeta completa sin perder los datos.

### Actualizar sin perder datos

El ZIP contiene **solo el programa, no tus fichas**. En este equipo los datos
están en `dist\FichasPerros\datos\`, dentro de la carpeta del programa: si
borras esa carpeta para volver a extraer el ZIP, te llevas por delante las
fichas, las fotos y los PDF.

Para actualizar sin perder nada: extrae el ZIP nuevo en **otra carpeta**, copia
la carpeta `datos` de la versión antigua a la nueva y abre el ejecutable nuevo.
En un PC donde `%LOCALAPPDATA%` sea escribible, copia en su lugar
`%LOCALAPPDATA%\FichasPerros`.

## Requisitos para ejecutar desde código fuente

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

Nota de compatibilidad: en este equipo Edge necesita arrancar con el sandbox
de Chromium desactivado para poder cargar la página local; por eso muestra una
advertencia. La ventana solo carga contenido de `127.0.0.1` y no navega a
sitios externos.

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
2. Cada entrada es una **hoja A4** con hasta cuatro perros y el estado de su
   PDF (generado o pendiente).
3. Abrir una hoja para ver sus perros; desde ahí se puede editar cada uno.
4. Si la hoja está pendiente, pulsar «Generar PDF de la hoja»; si ya está
   generada, «Ver PDF de la hoja».
5. «Eliminar hoja» borra la hoja y su PDF, pero conserva los perros y fotos.

La lista permite buscar por número de hoja, fecha o nombre del PDF.

Las importaciones agrupan las fotos nuevas en hojas de cuatro. La última hoja
incompleta también se genera, dejando los huecos en blanco.

### WhatsApp y PDF

1. Seleccionar un ZIP de exportación de WhatsApp.
2. Pulsar «Importar fotografías».
3. Consultar el resumen: encontradas, nuevas, duplicadas, descartadas y errores.
4. Al terminar se crea una ficha por cada foto nueva, se agrupan en **hojas de
   cuatro perros** y se genera un PDF por hoja. Los enlaces «Ver PDF» abren los
   documentos en el visor de Edge.
5. Si se vuelve a importar un ZIP con fotos ya incluidas, no se crean fichas,
   hojas ni PDF nuevos para esas fotos repetidas.
6. La galería y su botón «Generar PDF» siguen disponibles para crear otros
   documentos a partir de una selección manual.

Las imágenes se guardan con nombres internos únicos en la carpeta `fotos` de la
ubicación de datos indicada más abajo (`data/fotos` en desarrollo). En SQLite
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
fotografías ni los PDF ya generados; su hoja queda marcada como pendiente para
recordar que hay que regenerarla. Borrar una hoja no borra los perros.

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

Cada hoja conserva la relación con sus perros. Si una foto ya tenía ficha, se
reutiliza en lugar de crear otra. Editar una ficha no modifica los PDF que ya
se hubieran generado: la hoja queda como está hasta que se regenera.

Los documentos se guardan en la carpeta `documentos` de la ubicación de datos,
con un nombre único. El documento se abre desde la propia interfaz en el visor
de Edge, sin diálogo de guardado, y permanece en la carpeta de documentos para
imprimirlo o copiarlo cuando se quiera.

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

La suite tiene **36 pruebas**. Cubre importación, duplicados por SHA-256,
apertura de imágenes, conservación de hashes, rechazo de ZIP maliciosos,
gestión de fichas, agrupación en hojas de cuatro, migración de datos antiguos,
estados de PDF, borrado de hojas sin perder perros y ciclo de vida del servidor
de escritorio. La generación de PDF se ha validado con distintos números de
fotografías, incluida la última hoja incompleta.

También se probó la distribución onedir generada: arranque sin consola, ventana
de Edge, importación con creación automática de hojas y PDF, reimportación sin
duplicados, apertura y borrado de hojas, y cierre sin procesos residuales.

## Datos y compatibilidad

La base de datos existente se conserva y se amplía sin borrar nada. Las tablas
son `fotos`, `fichas`, `ficha_fotos`, `hojas`, `hoja_fichas` y `metadata`. La
primera vez que se abre una base antigua se agrupan las fichas existentes en
hojas de cuatro y se asocian los PDF por antigüedad. No se añadieron
dependencias de Python.

Durante el desarrollo se mantienen las carpetas actuales del proyecto:
`data/` y `documentos/`.

Cuando la aplicación está empaquetada, los datos persistentes se guardan en:

```text
%LOCALAPPDATA%\FichasPerros\
├── fichas.db
├── fotos\
├── documentos\
└── edge-profile\   (perfil interno de la ventana)
```

Las rutas se calculan sin depender del directorio de ejecución ni de `_MEIPASS`.
Para hacer una copia de seguridad basta con copiar esa carpeta completa.

Si el equipo impide escribir en `%LOCALAPPDATA%` (ocurre en Windows con
políticas restrictivas como este equipo de pruebas), la aplicación usa `datos\`
junto al ejecutable con la misma estructura. Se comprueba antes de arrancar;
cuando `%LOCALAPPDATA%` sí es escribible se usa esa ubicación y no se cambia
nada de los datos. Para saber dónde se están guardando las fichas, mira si
existe una carpeta `datos` junto a `FichasPerros.exe`.

## Solución de problemas

- **Windows no deja ejecutar el `.exe`**: pulsa «Más información» →
  «Ejecutar de todas formas». Es un programa sin firma digital.
- **Aparece «FichasPerros» con un error al abrir**: comprueba que Microsoft Edge
  está instalado y que la carpeta `datos` (o `%LOCALAPPDATA%\FichasPerros`) no
  está en solo lectura. El aviso muestra el motivo concreto.
- **La franja amarilla de Edge**: es la advertencia por `--no-sandbox`; ciérrala
  con la X. No impide usar la aplicación.
- **No se ve el PDF después de importar**: abre «Fichas» y comprueba el estado
  de la hoja. Si está «Pendiente», entra en ella y pulsa «Generar PDF de la
  hoja».
- **Quieres cambiar el equipo**: copia la carpeta del programa y la carpeta de
  datos; no hace falta exportar desde la aplicación.

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
├── hoja_service.py        # Hojas de 4 perros, PDF y borrado
├── whatsapp_import.py     # Importación segura de ZIP
├── pdf_generator.py       # Generación de fichas A4 en PDF
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── fichas_lista.html   # Lista de hojas
│   ├── hoja_detalle.html
│   ├── hoja_eliminar.html
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
    ├── test_hojas.py
    ├── test_flujo_importacion.py
    ├── test_documentos.py
    ├── test_desktop.py
    └── CREDITOS.md
```

La base de datos, las fotografías y los PDF generados son datos locales y no se
incluyen en Git. Las fotografías de los ZIP de prueba proceden de Wikimedia
Commons; sus autores y licencias se detallan en `pruebas/CREDITOS.md`.
