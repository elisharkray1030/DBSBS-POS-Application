Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildDir = Join-Path $RepoRoot "build"
$DistDir = Join-Path $RepoRoot "dist"
$VenvDir = Join-Path ([System.IO.Path]::GetTempPath()) "dbsbs-pos-build-$([guid]::NewGuid().ToString('N'))"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Executable = Join-Path $DistDir "DBSGardenFetePOS.exe"

$CustomTkinterVersion = "6.0.0"
$PyInstallerVersion = "6.22.3"

try {
    $PythonLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($null -eq $PythonLauncher) {
        throw "The Python launcher ('py') was not found. Install Python 3.11 and enable the Python launcher."
    }

    & $PythonLauncher.Source -3.11 -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python 3.11 build environment."
    }

    & $VenvPython -m pip install --disable-pip-version-check `
        "customtkinter==$CustomTkinterVersion" `
        "pyinstaller==$PyInstallerVersion"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install the pinned build dependencies."
    }

    New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

    & $VenvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name "DBSGardenFetePOS" `
        --collect-all customtkinter `
        --distpath $DistDir `
        --workpath (Join-Path $BuildDir "pyinstaller") `
        --specpath $BuildDir `
        (Join-Path $RepoRoot "main.pyw")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed to build DBSGardenFetePOS.exe."
    }

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "PyInstaller completed without producing $Executable."
    }

    $Hash = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "Built: $Executable"
    Write-Host "SHA256: $Hash"
}
finally {
    if (Test-Path -LiteralPath $VenvDir) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }
}
