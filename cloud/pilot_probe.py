"""Read-only public HTTPS pilot smoke tests; no credentials, no mutations."""
import ipaddress
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler


class PilotProbeError(RuntimeError):
    pass


def validate_base_url(raw):
    if not isinstance(raw, str):
        raise PilotProbeError('Se requiere un dominio HTTPS real del piloto')
    parsed = urlsplit(raw.strip())
    host = parsed.hostname
    if (parsed.scheme != 'https' or not host or parsed.username or parsed.password or
            parsed.port is not None or parsed.path not in ('', '/') or
            parsed.query or parsed.fragment or
            parsed.netloc.lower() != host or
            '.' not in host or host in ('localhost', '127.0.0.1') or
            host.endswith(('.local', '.localhost', '.invalid', '.test', '.example'))):
        raise PilotProbeError('Indica solo un dominio HTTPS público sin usuario, puerto, ruta ni parámetros')
    try:
        ipaddress.ip_address(host)
        raise PilotProbeError('Debe utilizarse un dominio verificado, no una dirección IP')
    except ValueError:
        pass
    return 'https://' + host


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def http_fetcher(base_url, timeout=10):
    """No redirects or authentication; TLS certificate checking remains enabled."""
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    def fetch(path):
        req = Request(base_url + path, headers={'Accept': 'application/json', 'User-Agent': 'MetroTaxi-Pilot-Probe/1.0'})
        try:
            with opener.open(req, timeout=timeout) as res:
                return res.status, dict(res.headers.items()), res.read(32768)
        except HTTPError as error:
            with error:
                return error.code, dict(error.headers.items()), error.read(32768)
        except (OSError, URLError) as error:
            raise PilotProbeError('Error al consultar la URL HTTPS: ' + str(error)) from error
    return fetch


def probe_pilot(base_url, fetch=None):
    """Check health and private access gate; never log customer data or secrets."""
    base_url=validate_base_url(base_url)
    fetch=fetch or http_fetcher(base_url)
    code, headers, body=fetch('/api/health')
    if code != 200:
        raise PilotProbeError('La API de salud no respondió 200 (HTTP ' + str(code) + ')')
    try:
        payload=json.loads(body)
    except (ValueError, TypeError):
        raise PilotProbeError('El endpoint de salud no devolvió JSON válido') from None
    if not isinstance(payload, dict) or payload.get('ok') is not True or payload.get('database') != 'ready':
        raise PilotProbeError('PostgreSQL todavía no figura como disponible en /api/health')
    checked=[]
    for path in ('/', '/ingresar.html', '/api/me', '/api/trips', '/map-config.js'):
        code, headers, body=fetch(path)
        if code != 401:
            raise PilotProbeError('Acceso sin contraseña permitido o no protegido: ' + path + ' (HTTP ' + str(code) + ')')
        basic=next((v for k,v in headers.items() if k.lower()=='www-authenticate'), '')
        if not basic.lower().startswith('basic '):
            raise PilotProbeError('Falta la protección HTTP Basic en ' + path)
        checked.append(path)
    return {'url':base_url, 'database':'ready', 'protected_paths':checked}
