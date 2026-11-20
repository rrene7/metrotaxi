@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
echo [1/3] Comprobando rutas, recursos y pruebas JavaScript...
%PY% scripts\validar_entrega.py --quick
if errorlevel 1 goto fallo
echo [2/3] Ejecutando TODAS las pruebas del servidor y permisos...
%PY% -m unittest discover -s tests -v
if errorlevel 1 goto fallo
echo [3/3] Validacion de nube (staging) y web Netlify...
%PY% scripts\validar_cloud.py
if errorlevel 1 goto fallo
echo.
echo VALIDACION AUTOMATICA APROBADA. Falta validar Chrome/Android antes de publicar.
pause
exit /b 0
:fallo
echo.
echo NO DISTRIBUIR: validacion incompleta o fallida.
pause
exit /b 1
