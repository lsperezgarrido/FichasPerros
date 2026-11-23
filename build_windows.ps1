# Genera la distribución Windows de FichasPerros (PyInstaller onedir).
# Ejecutar desde PowerShell en la raíz del proyecto:
#   .\build_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pyinstaller = Join-Path $PSScriptRoot ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyinstaller)) {
    throw "No se encontró PyInstaller en $pyinstaller"
}

if (Test-Path "dist\FichasPerros") {
    Remove-Item "dist\FichasPerros" -Recurse -Force
}

& $pyinstaller --noconfirm --clean "FichasPerros.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller terminó con error."
}

Copy-Item "LEEME_DISTRIBUCION.txt" "dist\FichasPerros\LEEME.txt" -Force

# Mantener actualizada la copia que viaja en el repositorio. Así, clonar el
# repo es suficiente para ejecutar el programa sin Python. Nunca se copia la
# carpeta "datos": los datos del usuario no se incluyen en el repositorio.
$app = Join-Path $PSScriptRoot "app"
if (Test-Path $app) {
    Remove-Item $app -Recurse -Force
}
New-Item -ItemType Directory -Path $app -Force | Out-Null
Copy-Item "dist\FichasPerros\FichasPerros.exe" -Destination $app -Force
Copy-Item "dist\FichasPerros\LEEME.txt" -Destination $app -Force
Copy-Item "dist\FichasPerros\_internal" -Destination $app -Recurse -Force

$zip = "dist\FichasPerros_Windows.zip"
if (Test-Path $zip) {
    Remove-Item $zip -Force
}
Compress-Archive -Path "dist\FichasPerros" -DestinationPath $zip

Write-Host ""
Write-Host "Distribución creada:"
Write-Host "  dist\FichasPerros\FichasPerros.exe"
Write-Host "  dist\FichasPerros\LEEME.txt"
Write-Host "  $zip"
Write-Host "  app\FichasPerros.exe  (copia incluida en el repositorio)"
