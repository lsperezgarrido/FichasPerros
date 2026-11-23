# Inicio rápido: clonar y usar

Este repositorio incluye la aplicación de Windows **ya compilada** en la carpeta
`app\`. No hace falta instalar Python, ni descargar nada, ni tener conexión.

## Pasos

1. Clona el repositorio:

   ```powershell
   git clone https://github.com/lsperezgarrido/FichasPerros
   ```

2. Entra en la carpeta `FichasPerros` resultante.

3. Ejecuta el programa:

   - Con doble clic: abre `app\FichasPerros.exe`.
   - O desde PowerShell: `.\app\FichasPerros.exe`

No ejecutes nada más. Instalar Python o ejecutar `build_windows.ps1` solo es
necesario si quieres modificar el código y volver a compilarlo.

## Cómo saber que ha funcionado

Después de unos segundos se abre una ventana de Microsoft Edge en modo
aplicación (sin barra de direcciones ni pestañas) con el título
**«Fichas de perros»**. Eso significa que la aplicación está lista.

Para cerrarla, cierra esa ventana. El servidor local se detiene solo.

## Avisos que pueden aparecer y no son errores

- **«No se pudo comprobar el editor» / «Editor desconocido»** de Windows: pulsa
  **Más información** → **Ejecutar de todas formas**. El ejecutable no tiene
  firma digital.
- **Franja amarilla de Edge sobre `--no-sandbox`**: ciérrala con la **X**. La
  ventana solo carga contenido local.
- **Cuadro «No se pudo iniciar FichasPerros»**: aquí sí hay un problema; el
  mensaje indica la causa (por ejemplo, Microsoft Edge no instalado o la
  carpeta de datos sin permisos de escritura).

## Datos

El repositorio **no incluye fotos, fichas ni PDF**: la aplicación arranca vacía.
No hay que crear ninguna carpeta ni configurar nada; se crea sola al primer uso.

Según el equipo, los datos se guardan en:

- `%LOCALAPPDATA%\FichasPerros\` (lo habitual en Windows), o
- `app\datos\`, junto al ejecutable, si Windows no permite escribir en
  `%LOCALAPPDATA%` (es el caso del equipo de desarrollo).

Para conservar o trasladar las fichas, copia esa carpeta de datos completa.

## Uso mínimo

1. En la pantalla **Inicio**, selecciona un ZIP de exportación de WhatsApp y
   pulsa **Importar fotografías**.
2. Se crean las fichas y se agrupan en **hojas de cuatro perros**, cada una con
   su PDF. En **Fichas** verás una entrada por hoja y su estado.
3. Abre una hoja para editar los datos de cada perro o ver su PDF.
4. Cierra la ventana cuando termines.

Para explicaciones detalladas, consulta `README.md`.
