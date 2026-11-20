#!/usr/bin/env python3
"""Validate v0.10 staging without mutating demo runtime or cloud databases."""
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def main():
    checks=[]
    node=shutil.which('node')
    if not node:
        print('ERROR: Node.js es obligatorio para validar la web staging')
        return 1
    for js in sorted((ROOT/'web-staging/js').glob('*.js')):
        checks.append(('Sintaxis '+js.name,[node,'--check',str(js)]))
    checks += [('Python Cloud Tests',[sys.executable,'-m','unittest','discover','-s','tests_cloud','-v'])]
    checks += [('Instalador Windows DEP-101',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_windows_staging_launcher_v101.py','-v'])]
    success=True
    for name,cmd in checks:
        print('\n==>',name,flush=True)
        try:
            p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=50)
            print((p.stdout+'\n'+p.stderr)[-6000:])
            if p.returncode:success=False
        except subprocess.TimeoutExpired:
            print('ERROR: timeout de pruebas');success=False
    print('RESULTADO CLOUD:', 'APROBADO (sin sustituir pruebas PostgreSQL/Android reales)' if success else 'FALLÓ')
    return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())
