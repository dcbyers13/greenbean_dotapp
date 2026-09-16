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


class StaticAssetsResolutionTestCase(SimpleTestCase):
    """Verify static asset resolution for brand styling and imagery."""

    def test_brand_css_resolves_http_200(self):
        """GET /static/css/brand.css must return HTTP 200."""
        response = self.client.get("/static/css/brand.css")
        self.assertEqual(response.status_code, 200)

    def test_logo_png_resolves_http_200(self):
        """GET /static/img/logo.png must return HTTP 200."""
        response = self.client.get("/static/img/logo.png")
        self.assertEqual(response.status_code, 200)

    def test_fallback_static_paths_resolve_http_200(self):
        """Fallback root static paths /static/brand.css and /static/logo.png must resolve HTTP 200."""
        css_resp = self.client.get("/static/brand.css")
        self.assertEqual(css_resp.status_code, 200)
        logo_resp = self.client.get("/static/logo.png")
        self.assertEqual(logo_resp.status_code, 200)

    def test_logo_backdrop_color_in_brand_css(self):
        """brand.css must configure the vibrant #99cb33 background for the logo medallion."""
        response = self.client.get("/static/css/brand.css")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content) if hasattr(response, "streaming_content") else response.content
        self.assertIn(b"#99cb33", content)
