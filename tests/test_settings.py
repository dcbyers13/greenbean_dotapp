"""Tests for Django configuration and settings invariants."""

import sys
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase


class SettingsConfigurationTestCase(SimpleTestCase):
    """Verify architectural invariants in settings."""

    def test_session_cookie_name(self):
        """SESSION_COOKIE_NAME must be namespaced to greenbean_sessionid."""
        self.assertEqual(settings.SESSION_COOKIE_NAME, "greenbean_sessionid")

    def test_csrf_cookie_name(self):
        """CSRF_COOKIE_NAME must be namespaced to greenbean_csrftoken."""
        self.assertEqual(settings.CSRF_COOKIE_NAME, "greenbean_csrftoken")

    def test_session_engine(self):
        """SESSION_ENGINE must use signed_cookies for lightweight statelessness."""
        self.assertEqual(
            settings.SESSION_ENGINE,
            "django.contrib.sessions.backends.signed_cookies",
        )

    def test_apps_directory_in_sys_path(self):
        """apps directory must be on sys.path for clean submodule imports."""
        apps_path = str(settings.BASE_DIR / "apps")
        self.assertIn(apps_path, sys.path)

    def test_static_files_configuration(self):
        """Static file settings must support WhiteNoise and local static dir."""
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertTrue(bool(settings.STATIC_ROOT))

        static_dir = settings.BASE_DIR / "static"
        self.assertTrue(any(Path(d).resolve() == static_dir.resolve() for d in settings.STATICFILES_DIRS))

        # Check WhiteNoise middleware
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)

        # Check WhiteNoise storage backend
        staticfiles_backend = settings.STORAGES.get("staticfiles", {}).get("BACKEND")
        self.assertEqual(
            staticfiles_backend,
            "whitenoise.storage.CompressedStaticFilesStorage",
        )
