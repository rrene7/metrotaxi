"""LOCAL-118: guardrails for offline Docker/PostgreSQL staging.

No Docker daemon, network, or real secrets needed in CI.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalDockerPilotChecks(unittest.TestCase):
    def test_local_app_and_database_are_not_public(self):
        compose = (ROOT / "compose.local.yaml").read_text(encoding="utf-8")
        self.assertIn('127.0.0.1:8770:8080', compose)
        self.assertNotRegex(compose, r"(?m)^\s+-\s*['\"]?5432:")
        self.assertIn('internal: true', compose)
        self.assertIn('networks: [metro_private, metro_loopback]', compose)
        self.assertIn('metro_loopback:', compose)
        self.assertIn('driver: bridge', compose)
        self.assertIn('metro_local_pgdata:/var/lib/postgresql/data', compose)
        self.assertIn('postgres:16-alpine', compose)
        self.assertIn("service_healthy", compose)
        self.assertIn('cloud.local_docker:app', compose)
        self.assertNotIn("cloud.preview:app", compose)
        self.assertNotIn("METRO_BOOTSTRAP_EMPTY_DB", compose)

    def test_private_credentials_are_not_committed_or_built(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn('/metro-local.env', ignore)
        self.assertIn('metro-local.env', dockerignore)
        compose = (ROOT / "compose.local.yaml").read_text(encoding="utf-8")
        self.assertIn('${METRO_LOCAL_DB_PASSWORD:?', compose)
        example = (ROOT / "metro-local.example.env").read_text(encoding="utf-8")
        self.assertIn("REEMPLAZAR_", example)

    def test_local_entrypoint_cannot_bootstrap_and_uses_only_test_mode(self):
        source = (ROOT / "cloud/local_docker.py").read_text(encoding="utf-8")
        self.assertIn("normalize_postgres_url(", source)
        self.assertIn("parsed.host != 'db'", source)
        self.assertIn("parsed.database != 'metrotaxi_local'", source)
        self.assertIn("test_mode=True, auto_create=False", source)
        self.assertIn("allow_empty_bootstrap=False", source)
        self.assertIn("loopback_host_only", source)
        self.assertIn("status_code=403", source)
        self.assertIn("127.0.0.1", source)
        self.assertIn("StaticFiles(", source)

    def test_factory_only_prevents_cli_from_building_unrelated_public_app(self):
        compose = (ROOT / "compose.local.yaml").read_text(encoding="utf-8")
        api = (ROOT / "cloud/app.py").read_text(encoding="utf-8")
        self.assertIn('METRO_FACTORY_ONLY: "1"', compose)
        self.assertIn("os.environ.get('METRO_FACTORY_ONLY') != '1'", api)
        self.assertIn("app = create_app()", api)
        self.assertIn("app = None", api)

    def test_real_docker_smoke_is_mandatory_after_unit_tests(self):
        ci = (ROOT / ".github/workflows/validar.yml").read_text(encoding="utf-8")
        smoke = (ROOT / "scripts/smoke_local_docker.py").read_text(encoding="utf-8")
        self.assertIn("docker-local-smoke:", ci)
        self.assertIn("needs: pruebas", ci)
        self.assertIn("python3 scripts/smoke_local_docker.py", ci)
        self.assertIn('GITHUB_ACTIONS', smoke)
        self.assertIn('docker", "compose"', smoke)
        self.assertIn('"--init-schema"', smoke)
        self.assertIn('"/api/health"', smoke)
        self.assertIn('"/ingresar.html"', smoke)
        self.assertIn('"/api/me"', smoke)
        self.assertIn('"Origin": BASE', smoke)
        self.assertIn('"Host": "outside.example"', smoke)
        self.assertIn('"start", "app"', smoke)
        self.assertIn('"stop", "app", "db"', smoke)
        self.assertNotIn('down -v', smoke)

    def test_runbook_uses_safe_initialization_and_preserves_volumes(self):
        doc = (ROOT / "docs/PILOTO_DOCKER_LOCAL.md").read_text(encoding="utf-8")
        self.assertIn("--init-schema", doc)
        self.assertIn("--create-admin", doc)
        self.assertIn("--create-driver", doc)
        self.assertIn("docker compose --env-file metro-local.env -f compose.local.yaml", doc)
        self.assertNotIn("down -v", doc)
        self.assertIn("127.0.0.1:8770", doc)
        self.assertIn("No abrir puertos", doc)


if __name__ == "__main__":
    unittest.main()
