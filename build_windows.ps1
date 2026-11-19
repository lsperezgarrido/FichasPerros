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
