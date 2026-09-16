import os
from pathlib import Path
from django.conf import settings
from django.test import TestCase


class ContainerConfigurationTestCase(TestCase):
    """Verify production containerization assets, entrypoint script, and build configuration."""

    def setUp(self):
        self.repo_root = Path(settings.BASE_DIR)
        self.dockerfile = self.repo_root / "Dockerfile"
        self.entrypoint = self.repo_root / "docker-entrypoint.sh"
        self.dockerignore = self.repo_root / ".dockerignore"
        self.env_example = self.repo_root / ".env.example"

    def test_container_files_exist_at_repo_root(self):
        """Dockerfile, docker-entrypoint.sh, and .dockerignore must exist at the root."""
        self.assertTrue(self.dockerfile.is_file(), "Dockerfile missing from repository root")
        self.assertTrue(self.entrypoint.is_file(), "docker-entrypoint.sh missing from repository root")
        self.assertTrue(self.dockerignore.is_file(), ".dockerignore missing from repository root")
        self.assertTrue(self.env_example.is_file(), ".env.example missing from repository root")

    def test_docker_entrypoint_permissions_and_contents(self):
        """docker-entrypoint.sh must be executable, use LF line endings, and run migrations."""
        self.assertTrue(os.access(self.entrypoint, os.X_OK), "docker-entrypoint.sh must be executable")

        content = self.entrypoint.read_text(encoding="utf-8")
        self.assertNotIn("\r\n", content, "docker-entrypoint.sh must use Linux LF line endings")
        self.assertTrue(content.startswith("#!/usr/bin/env bash"), "Missing shebang")
        self.assertIn("set -euo pipefail", content)
        self.assertIn("python manage.py migrate --noinput", content)
        self.assertIn('exec "$@"', content)

    def test_dockerfile_multi_stage_and_security_invariants(self):
        """Dockerfile must implement multi-stage build and rootless 10001:10001 runtime execution."""
        content = self.dockerfile.read_text(encoding="utf-8")

        # Verify multi-stage build stages
        self.assertIn("FROM python:3.12-slim AS builder", content)
        self.assertIn("FROM python:3.12-slim AS runtime", content)
        self.assertIn("COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/", content)

        # Verify rootless non-root unprivileged service user (UID 10001, GID 10001)
        self.assertIn("groupadd -g 10001 appuser", content)
        self.assertIn("useradd -u 10001 -g appuser", content)
        self.assertIn("USER appuser", content)

        # Verify collectstatic during build stage
        self.assertIn("collectstatic --noinput", content)

        # Verify entrypoint and Gunicorn CMD
        self.assertIn('ENTRYPOINT ["/app/docker-entrypoint.sh"]', content)
        self.assertIn("gunicorn", content)
        self.assertIn("config.wsgi:application", content)

    def test_dockerignore_rules(self):
        """.dockerignore must exclude build artifacts, virtualenvs, databases, and secrets."""
        rules = set(line.strip() for line in self.dockerignore.read_text(encoding="utf-8").splitlines() if line.strip())
        expected_patterns = {".git", ".venv", "__pycache__", "*.sqlite3", "db.sqlite3", "staticfiles/", "media/", "tests/", ".env*"}
        for pattern in expected_patterns:
            self.assertIn(pattern, rules, f"Expected {pattern} in .dockerignore")

    def test_env_example_production_keys(self):
        """.env.example must specify required production environment keys."""
        content = self.env_example.read_text(encoding="utf-8")
        self.assertIn("DEBUG=False", content)
        self.assertIn("SECRET_KEY=", content)
        self.assertIn("ALLOWED_HOSTS=", content)
        self.assertIn("DATABASE_URL=", content)
