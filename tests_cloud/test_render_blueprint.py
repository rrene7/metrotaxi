"""Validate Render Free blueprint has no secrets and cannot silently deploy production."""
import unittest
from pathlib import Path


class RenderBlueprintChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[1]
        cls.blueprint=(cls.root/'render.yaml').read_text(encoding='utf-8')
        cls.guide=(cls.root/'docs/RENDER_AIVEN_NETLIFY.md').read_text(encoding='utf-8')

    def test_free_docker_web_not_postgres(self):
        self.assertIn('type: web',self.blueprint)
        self.assertIn('runtime: docker',self.blueprint)
        self.assertIn('plan: free',self.blueprint)
        self.assertIn('dockerfilePath: ./Dockerfile',self.blueprint)
        self.assertIn('healthCheckPath: /api/health',self.blueprint)
        self.assertNotIn('databases:',self.blueprint)
        self.assertIn('autoDeployTrigger: checksPass',self.blueprint)

    def test_critical_configuration_requested_not_embedded(self):
        b=self.blueprint
        for var in ('DATABASE_URL','METRO_ALLOWED_ORIGINS','METRO_ALLOWED_HOSTS','METRO_BOOTSTRAP_EMPTY_DB'):
            self.assertIn('key: '+var+'\n        sync: false',b)
        self.assertIn('key: METRO_PILOT_PASSWORD\n        generateValue: true',b)
        self.assertNotIn('password123',b)
        self.assertNotIn('postgresql://',b)
        self.assertNotIn('postgresql+psycopg://',b)
        self.assertNotIn('api.example.com',b)
        self.assertNotIn('value: "1"',b)

    def test_netlify_cannot_replace_api_and_secrets_are_outside_git(self):
        self.assertIn('Netlify',self.guide)
        self.assertIn('Aiven',self.guide)
        self.assertIn('Render',self.guide)
        self.assertIn('no es producción',self.guide.lower())
        docker=(self.root/'Dockerfile').read_text()
        self.assertIn('cloud.pilot:app',docker)
        self.assertIn('USER metro',docker)
        self.assertIn('.env', (self.root/'.dockerignore').read_text())

if __name__=='__main__': unittest.main()
