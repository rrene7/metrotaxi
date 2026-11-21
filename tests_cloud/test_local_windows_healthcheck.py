"""LOCAL-121: Windows pilot diagnostic remains read-only and checks wrong-server regression."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'verificar_metro_local.ps1'


class LocalHealthcheckTests(unittest.TestCase):
    def test_diagnostic_checks_port_owner_actual_docker_binding_and_api(self):
        script = SCRIPT.read_text(encoding='utf-8')
        for marker in ('Get-NetTCPConnection', 'Get-Process', 'docker compose',
                       'docker inspect', '.NetworkSettings.Ports', 'HostIp',
                       'HostPort', '/api/health', '/ingresar.html?revision=local121',
                       'id="ver-clave"', 'RESULTADO: ENTORNO LOCAL CORRECTO'):
            self.assertIn(marker, script)

    def test_no_destructive_commands_or_secrets(self):
        text = SCRIPT.read_text(encoding='utf-8').lower()
        for forbidden in ('stop-process', 'down -v', 'volume rm', 'docker rm',
                          'remove-item', 'docker compose up', 'docker compose down',
                          'password_hash', 'metro_local_db_password'):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
