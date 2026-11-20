#!/usr/bin/env python3
"""Metro Taxi: puerta de calidad que NO modifica runtime ni genera datos de clientes."""
import argparse
import ast
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DOCS = (
    'RUTA_DE_TRABAJO.md', 'AGENTS.md', 'README.md',
    'docs/INCIDENTES_Y_SOLUCIONES.md',
    'docs/CONTRATO_OPERATIVO.md',
    'docs/PRUEBAS_DE_ACEPTACION.md',
)


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        info = dict(attrs)
        if tag in ('script', 'img'):
            u = info.get('src', '')
        elif tag == 'link':
            u = info.get('href', '')
        else:
            return
        if u.startswith(('/static/', '/sw.js', '/manifest-')):
            self.assets.append(u.split('?', 1)[0])


def allowed_static_routes():
    """Read allowlist from actual Handler.do_GET, not an unrelated duplicated list."""
    tree = ast.parse((ROOT / 'server.py').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name) or node.left.id != 'p':
            continue
        if len(node.ops) != 1 or not isinstance(node.ops[0], ast.In):
            continue
        if not isinstance(node.comparators[0], (ast.Tuple, ast.List)):
            continue
        values = [elt.value for elt in node.comparators[0].elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
        if '/static/driver.js' in values:
            return set(values)
    raise ValueError('No encontré una lista verificable de recursos en Handler.do_GET')


def check_files():
    errors = []
    for name in REQUIRED_DOCS:
        if not (ROOT / name).is_file():
            errors.append('Falta documento de trabajo: ' + name)
    text = (ROOT / '.gitignore').read_text(encoding='utf-8') if (ROOT / '.gitignore').is_file() else ''
    for exclusion in ('/runtime/', '.env', '*.sqlite3'):
        if exclusion not in text:
            errors.append('Falta excluir secretos o datos en .gitignore: ' + exclusion)
    if (ROOT / 'runtime').exists():
        # A local checkout can contain data; just warn, never remove it.
        print('AVISO: runtime/ contiene datos locales; no incluirlos al empaquetar ni en GitHub.')
    try:
        allowed = allowed_static_routes()
        for html in sorted(ROOT.glob('*.html')):
            parser = AssetParser()
            parser.feed(html.read_text(encoding='utf-8'))
            for asset in parser.assets:
                if asset not in allowed:
                    errors.append(f'{html.name}: recurso {asset} NO autorizado por servidor')
                if not (ROOT / asset.lstrip('/')).is_file():
                    errors.append(f'{html.name}: recurso {asset} NO existe')
    except Exception as e:
        errors.append(f'No se pudo revisar recursos: {e}')
    conductor = (ROOT / 'conductor.html').read_text(encoding='utf-8')
    driver = (ROOT / 'static/driver.js').read_text(encoding='utf-8')
    if 'static/navigation.js' in conductor or 'window.MTNavigation' in driver:
        errors.append('Regresión LOAD-084: la lista de carreras vuelve a depender de navigation.js')
    if 'data-refresh-trips' not in driver or 'finally{loadingServices=false}' not in driver:
        errors.append('Regresión LOAD-084: falta aviso/reintento o desbloqueo de carga')
    if not (ROOT / 'tests/test_driver_loading_v084.cjs').is_file():
        errors.append('Falta prueba de regresión LOAD-084')
    return errors


def run(name, args):
    """Use a temporary file instead of a PIPE: the HTTP tests log heavily."""
    print(f'\n==> {name}:', ' '.join(args), flush=True)
    # Avoid indefinite hangs and do not depend on Python buffering/pipe behavior.
    limit = 45 if name.startswith('API ') else 40
    with tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as log:
        try:
            result = subprocess.run(args, cwd=ROOT, text=True, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=limit, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            log.seek(0)
            for line in log.read().splitlines()[-45:]:
                print(line)
            print(f'ERROR: ejecución interrumpida en {name}: {e}')
            return False
        log.seek(0)
        output = log.read().strip().splitlines()
        if result.returncode:
            for line in output[-65:]:
                print(line)
            print(f'ERROR {name}: código {result.returncode}')
            return False
        if output:
            for line in output[-4:]:
                print(line)
        print(f'OK: {name}')
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--quick', action='store_true', help='Documentos, assets y JS sin pruebas HTTP')
    group.add_argument('--full', action='store_true', help='Todo el proyecto, incluyendo pruebas Python')
    args = parser.parse_args()
    print('METRO TAXI v0.10 — validador legado + regresiones (no modifica runtime)')
    errors = check_files()
    if errors:
        for error in errors:
            print('ERROR:', error)
        return 1
    print('OK: ruta de trabajo, privacidad, documentación y dependencias HTML/servidor')
    node = shutil.which('node')
    if not node:
        print('ERROR: se requiere Node.js para validar sintaxis y pruebas JS. No distribuir sin completar validación.')
        return 1
    files_js = sorted((ROOT / 'static').glob('*.js')) + [ROOT / 'sw.js']
    ok = True
    for f in files_js:
        ok = run('Sintaxis ' + f.name, [node, '--check', str(f)]) and ok
    for f in sorted((ROOT / 'tests').glob('test_*.cjs')):
        ok = run('Regresión ' + f.name, [node, str(f)]) and ok
    if not args.quick:
        # Keep API test modules in separate processes to isolate their HTTP-server,
        # session, temporary SQLite files and threads. A stuck module fails on timeout.
        for test_module in sorted((ROOT / 'tests').glob('test_*.py')):
            ok = run('API ' + test_module.name,
                     [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                      '-p', test_module.name, '-v']) and ok
    print('\nRESULTADO:', 'VALIDACIÓN AUTOMÁTICA APROBADA' if ok else 'FALLÓ: NO DISTRIBUIR')
    if ok:
        print('PENDIENTE: aceptación visual y pruebas en teléfono físico (no cubiertas aquí).')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
