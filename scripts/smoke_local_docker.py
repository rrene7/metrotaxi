#!/usr/bin/env python3
"""LOCAL-119: disposable CI-only real Docker/PostgreSQL smoke test.

Runs only on GitHub Actions. Does not create or remove user volumes.
No external network access from the Metro Taxi containers.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8770"


def require_ci():
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise SystemExit("Prueba Docker reservada a un runner efímero de GitHub Actions.")


def run(compose, *args):
    subprocess.run([*compose, *args], cwd=ROOT, check=True, timeout=360)


def http(opener, path, method="GET", body=None, headers=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(BASE + path, data=payload, method=method, headers=headers or {})
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=8) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def until_ready(opener):
    for _ in range(40):
        try:
            status, body, _ = http(opener, "/api/health")
            if status == 200 and json.loads(body).get("database") == "ready":
                return
        except (URLError, TimeoutError, ValueError):
            pass
        time.sleep(2)
    raise AssertionError("Contenedor Metro Taxi no informó PostgreSQL disponible")


def main():
    require_ci()
    with tempfile.TemporaryDirectory(prefix="mt-docker-ci-") as temp:
        password = secrets.token_hex(24)
        env_file = Path(temp) / "metro-local.env"
        env_file.write_text("METRO_LOCAL_DB_PASSWORD=" + password + "\n", encoding="utf-8")
        compose = ["docker", "compose", "--env-file", str(env_file),
                   "-p", "metrotaxi_ci_smoke", "-f", "compose.local.yaml"]
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        try:
            run(compose, "config", "--quiet")
            run(compose, "build", "app")
            run(compose, "up", "-d", "db")
            run(compose, "run", "--rm", "-T", "app", "python", "-m", "cloud.manage", "--init-schema")
            # Credentials are ephemeral and never used with real customer data.
            script = ("import os; from sqlalchemy import create_engine; "
                      "from cloud.manage import create_staff; "
                      "e=create_engine(os.environ['DATABASE_URL']); "
                      "create_staff(e,'ci_smoke_admin','ci-only-admin-password-123456'); e.dispose()")
            run(compose, "run", "--rm", "-T", "app", "python", "-c", script)
            run(compose, "up", "-d", "app")
            until_ready(opener)

            status, page, _ = http(opener, "/ingresar.html")
            assert status == 200 and b"<html" in page.lower(), "Login web unavailable"
            status, _, _ = http(opener, "/api/me", headers={"Host": "outside.example"})
            assert status == 403, "External Host header was not rejected"
            status, _, _ = http(opener, "/api/login", method="POST",
                                body={"username": "ci_smoke_admin", "password": "bad"},
                                headers={"Origin": "https://evil.invalid"})
            assert status == 403, "Origin guard was relaxed"
            status, _, _ = http(opener, "/api/login", method="POST",
                                body={"username": "ci_smoke_admin",
                                      "password": "ci-only-admin-password-123456"},
                                headers={"Origin": BASE})
            assert status == 200, "Browser login failed on actual Docker HTTP origin"
            status, body, _ = http(opener, "/api/me")
            assert status == 200 and json.loads(body).get("authenticated") is True, "Session not persisted"
            assert json.loads(body)["user"]["role"] == "admin"
            # Stop and restart without removing database volume, then re-login.
            run(compose, "stop", "app", "db")
            run(compose, "start", "db")
            run(compose, "start", "app")
            until_ready(opener)
            status, body, _ = http(opener, "/api/me")
            assert status == 200 and json.loads(body).get("authenticated") is True, (
                "Existing account/session disappeared after container restart")
            print("LOCAL-119 OK: Docker/PostgreSQL boot, Origin/Host/session, persistence")
        finally:
            # Stop only. Never delete named volumes or run 'down -v'.
            run(compose, "stop", "app", "db")


if __name__ == "__main__":
    main()
