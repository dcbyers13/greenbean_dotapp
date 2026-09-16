"""Tests for web views and template rendering."""

from django.test import SimpleTestCase
from django.urls import reverse


class SplashViewTestCase(SimpleTestCase):
    """Verify splash view HTTP behavior, template rendering, and brand elements."""

    def test_splash_url_resolves_and_returns_200(self):
        """The root URL `/` must return HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_splash_reverse_url(self):
        """The named URL `core:splash` must reverse to `/` and return HTTP 200."""
        url = reverse("core:splash")
        self.assertEqual(url, "/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_splash_template_rendered(self):
        """Splash view must render core/splash.html extending base.html."""
        response = self.client.get("/")
        self.assertTemplateUsed(response, "core/splash.html")
        self.assertTemplateUsed(response, "base.html")

    def test_splash_references_brand_logo(self):
        """Response content must reference the brand logo in static/img/logo.png."""
        response = self.client.get("/")
        self.assertContains(response, "logo.png")

    def test_splash_displays_mission_statement(self):
        """Response must display the exact brand mission statement."""
        expected_mission = (
            "Worker-owned, community-powered coffee. "
            "Sourced ethically, roasted locally, and rooted in our neighborhood."
        )
        response = self.client.get("/")
        self.assertContains(response, expected_mission)

    def test_splash_displays_status_badges(self):
        """Response must include all three required status badges."""
        response = self.client.get("/")
        self.assertContains(response, "Est. 2017")
        self.assertContains(response, "Domain Secured: greenbean.app")
        self.assertContains(response, "Phase 1: Operational")
