import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from api.index import _TITLE_CACHE, app
from api.network import FetchedResource, FetchError


def fake_resolver(host, port):
    import ipaddress

    from api.network import resolve_public_address

    try:
        ipaddress.ip_address(host)
    except ValueError:
        return "93.184.216.34"
    return resolve_public_address(host, port)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.resolver = patch("api.index.resolve_public_address", side_effect=fake_resolver)
        self.resolver.start()
        self.addCleanup(self.resolver.stop)
        _TITLE_CACHE._entries.clear()
        _TITLE_CACHE._bytes = 0
        self.client = app.test_client()

    def test_missing_and_invalid_urls(self):
        for path in ("/info", "/badge"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 400)
            self.assertEqual(
                self.client.get(path, query_string={"url": "file:///etc/passwd"}).status_code, 400
            )
            self.assertEqual(
                self.client.get(path, query_string={"url": "https://127.0.0.1"}).status_code, 400
            )
            self.assertEqual(
                self.client.get(path + "?url=https://example.com&" + "x" * 9000).status_code, 414
            )

    @patch(
        "api.index.fetch_public_bytes",
        return_value=FetchedResource(
            b"<html><head><title>Example &amp; Co</title></head><body>Huge body</body></html>",
            "text/html",
        ),
    )
    def test_info_and_badge_share_title_cache(self, fetch):
        info = self.client.get("/info?url=example.com")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.json["title"], "Example & Co")
        self.assertEqual(info.json["url"], "https://example.com/")
        badge = self.client.get("/badge?url=example.com&embed=false")
        self.assertEqual(badge.status_code, 200)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(badge.mimetype, "image/svg+xml")
        self.assertEqual(badge.headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(badge.headers["X-Content-Type-Options"], "nosniff")
        ET.fromstring(badge.data)

    @patch("api.index.fetch_public_bytes", side_effect=FetchError("offline"))
    def test_metadata_failure_preserves_fallback(self, fetch):
        response = self.client.get("/info?url=https://example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["title"], "Website Link")
        self.assertTrue(
            response.json["image_url"].startswith("https://s0.wordpress.com/mshots/v1/")
        )

    @patch("api.index.fetch_public_bytes")
    @patch("api.card.fetch_public_bytes")
    def test_custom_title_skips_metadata_fetch(self, image_fetch, html_fetch):
        image_fetch.side_effect = FetchError("offline")
        response = self.client.get(
            "/badge?url=example.com&custom_title=Custom&title_opacity=nan&image_scale=inf&height=999999&title_color=%23abc"
        )
        self.assertEqual(response.status_code, 200)
        html_fetch.assert_not_called()
        root = ET.fromstring(response.data)
        self.assertEqual(root.attrib["aria-label"], "Custom")
        self.assertEqual(root.attrib["height"], "1000")
        self.assertNotIn("nan", response.get_data(as_text=True).lower())
        self.assertNotIn("inf", response.get_data(as_text=True).lower())

    def test_static_assets_and_traversal_protection(self):
        with self.client.get("/") as response:
            self.assertEqual(response.status_code, 200)
        with self.client.get("/app.js") as response:
            self.assertEqual(response.mimetype, "application/javascript")
        with self.client.get("/i18n/index.js") as response:
            self.assertEqual(response.status_code, 200)
        with self.client.get("/i18n/locales/en.js") as response:
            self.assertEqual(response.status_code, 200)
        with self.client.get("/i18n/../requirements.txt") as response:
            self.assertEqual(response.status_code, 404)
        with self.client.get("/i18n/%2e%2e/%2e%2e/etc/passwd") as response:
            self.assertEqual(response.status_code, 404)
        response = self.client.get("/")
        response.close()
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
