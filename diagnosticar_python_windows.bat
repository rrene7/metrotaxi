@echo off
setlocal
cd /d "%~dp0"
echo === VERSIONES DE PYTHON ===
py -0p
echo.
echo === VERSION DE WINDOWS ===
ver
echo.
echo === ENTORNO STAGING (si existe) ===
for %%V in (312 311 313) do (
  if exist ".venv-staging-%%V\Scripts\python.exe" (
    echo .venv-staging-%%V:
    ".venv-staging-%%V\Scripts\python.exe" --version
    ".venv-staging-%%V\Scripts\python.exe" -m pip --version
  )
)
echo.
pause
