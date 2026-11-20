@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)
%PYTHON% --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Instala Python 3.10 o superior y vuelve a ejecutar.
  pause
  exit /b 1
)
%PYTHON% -c "import qrcode; import qrcode.image.svg" >nul 2>nul
if errorlevel 1 (
  echo Preparando libreria QR para Metro Taxi...
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo No se pudo instalar la libreria QR. Comprueba la conexion a Internet.
    pause
    exit /b 1
  )
)
echo Metro Taxi desarrollo v0.8.4. No publiques este servidor HTTP en Internet.
%PYTHON% server.py
pause
