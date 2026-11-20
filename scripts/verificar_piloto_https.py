#!/usr/bin/env python3
"""Read-only deployment check: python -m scripts.verificar_piloto_https --url https://..."""
import argparse
import os
from cloud.pilot_probe import PilotProbeError, probe_pilot


def main():
    p=argparse.ArgumentParser(description='Verifica HTTPS, PostgreSQL y protección del piloto Metro Taxi sin credenciales')
    p.add_argument('--url',help='URL pública de Railway, ej. https://tu-dominio.up.railway.app')
    opts=p.parse_args()
    candidate=opts.url or os.environ.get('METRO_PILOT_URL','')
    try:
        result=probe_pilot(candidate)
    except PilotProbeError as error:
        print('PILOTO NO VALIDADO:',error)
        return 1
    print('PILOTO VERIFICADO:',result['url'])
    print('PostgreSQL:',result['database'])
    print('Rutas protegidas:',len(result['protected_paths']))
    print('Esto NO verifica cuentas ni GPS físico. No admite tráfico real todavía.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
