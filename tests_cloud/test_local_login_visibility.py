"""LOCAL-120: login form must permit verifying exactly what the browser submits."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LocalLoginVisibilityTests(unittest.TestCase):
    def test_form_exposes_reveal_control_and_fresh_assets(self):
        html = (ROOT / 'web-staging/ingresar.html').read_text(encoding='utf-8')
        self.assertIn('id="ver-clave"', html)
        self.assertIn('Mostrar contraseña', html)
        self.assertIn('autocomplete="current-password"', html)
        self.assertIn('/js/api.js?v=local-120', html)
        self.assertIn('/js/login.js?v=local-120', html)

    def test_password_is_not_trimmed_or_logged(self):
        script = (ROOT / 'web-staging/js/login.js').read_text(encoding='utf-8')
        self.assertIn('const pass=password.value;', script)
        self.assertIn('password:pass', script)
        self.assertIn("reveal.checked?'text':'password'", script)
        self.assertIn('button.disabled=true', script)
        self.assertNotRegex(script, r'password\.value\.trim\(')
        self.assertNotRegex(script, r'console\.(log|debug|error)\s*\(')


if __name__ == '__main__':
    unittest.main()
