"""Generate a deployable static folder only AFTER a trusted HTTPS API exists."""
import argparse
import shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent.parent


def build(api_url, output):
    u=urlparse(api_url)
    if (u.scheme!='https' or not u.netloc or u.username or u.password or u.path not in ('','/')
            or u.query or u.fragment or u.hostname in ('localhost','127.0.0.1')
            or u.hostname.endswith(('.invalid','.example','.test','.localhost'))):
        raise ValueError('Se necesita una URL REAL https://api.dominio.com, sin ruta ni secretos')
    output=Path(output).resolve()
    if output == ROOT or ROOT in output.parents and output.name=='web-staging':
        raise ValueError('No sobrescribir el código fuente de la web')
    if output.exists():
        raise ValueError('La carpeta de salida ya existe; elige otra para evitar borrar archivos')
    shutil.copytree(ROOT/'web-staging', output)
    (output/'_redirects').write_text('/api/* '+api_url.rstrip('/')+'/api/:splat 200\n',encoding='utf-8')
    (output/'README_NETLIFY.txt').write_text(
      'METRO TAXI · STAGING. Publicar SOLO después de que la API HTTPS esté operativa y protegida.\n'
      'La regla /api/* usa un proxy Netlify; verificar cookies, sesiones, CSRF y Origin reales.\n'
      'No subir contraseñas, archivos runtime ni SQLite. No apto aún para producción.\n',encoding='utf-8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--api-url',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print('Carpeta Netlify generada:',build(a.api_url,a.output))
