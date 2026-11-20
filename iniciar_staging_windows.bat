@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title METRO TAXI v0.10.1 - INSTALACION STAGING

echo ==============================================================
echo METRO TAXI - PRUEBAS EN WINDOWS
 echo Python requerido: 3.11, 3.12 o 3.13 de 64 bits.
echo ==============================================================
echo.

REM Seleccionar una version concreta, NO py -3 (puede elegir Python 3.9).
set "PYVER="
for %%V in (3.12 3.11 3.13) do (
    if not defined PYVER (
        py -%%V -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==64 else 1)" >nul 2>&1 && set "PYVER=%%V"
    )
)
if not defined PYVER (
    echo ERROR: No se encontro Python 3.11, 3.12 o 3.13 de 64 bits.
    echo Tu instalador anterior usaba Python 3.9, incompatible con esta etapa.
    echo Descarga Python 3.12 para Windows x64 desde:
    echo https://www.python.org/downloads/windows/
    echo Despues abre una NUEVA ventana y ejecuta este archivo.
    echo Para ver tus versiones instaladas: py -0p
    pause
    exit /b 1
)

echo [1/4] Python %PYVER% de 64 bits detectado.
set "VENV_DIR=.venv-staging-%PYVER:.=%"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [2/4] Creando entorno virtual aislado %VENV_DIR%...
    py -%PYVER% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :FALLO_VENV
) else (
    echo [2/4] Reutilizando entorno %VENV_DIR%.
)
"%VENV_PY%" -c "import sys,struct; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)] and struct.calcsize('P')*8==64"
if errorlevel 1 goto :FALLO_VENV

echo [3/4] Preparando pip del entorno aislado...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :FALLO_DEP

echo [4/4] Instalando SOLO ruedas binarias, sin compilar greenlet...
"%VENV_PY%" -m pip install --only-binary=:all: -r "cloud\requirements.txt"
if errorlevel 1 goto :FALLO_DEP

echo.
echo Instalacion completada. Abre: http://127.0.0.1:8770/
echo Datos de prueba: _runtime_staging\credenciales_cloud_demo.txt
echo Para detener el servidor, presiona Ctrl+C.
"%VENV_PY%" -m uvicorn cloud.preview:app --host 127.0.0.1 --port 8770
if errorlevel 1 (
    echo.
    echo El servidor termino con un error. Revisa el mensaje anterior.
)
pause
exit /b 0

:FALLO_VENV
echo.
echo ERROR al crear o utilizar el entorno Python. No se modificaron las bases runtime.
echo Comprueba con: py -0p
pause
exit /b 1

:FALLO_DEP
echo.
echo ERROR al instalar dependencias.
echo No se intentara compilar paquetes en Windows.
echo Comprueba que tengas Internet y Windows x64 con Python compatible.
echo Si hay un error de version, envia el texto completo del mensaje.
pause
exit /b 1
