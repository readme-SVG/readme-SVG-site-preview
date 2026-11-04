import base64
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from api.card import fetch_image_as_base64, generate_svg
from api.network import FetchedResource, FetchError

PNG = b"\x89PNG\r\n\x1a\n" + b"test-image"


class CardTests(unittest.TestCase):
    def test_svg_escapes_untrusted_text_and_url(self):
        title = "<script>alert(\"x\")</script> & 'title'"
        svg = generate_svg(title, 'https://s0.wordpress.com/a?x=1&y="bad"', embed_thumbnail=False)
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib["aria-label"], title)
        self.assertNotIn("<script", svg)
        image = root.find("{http://www.w3.org/2000/svg}image")
        self.assertEqual(image.attrib["href"], 'https://s0.wordpress.com/a?x=1&y="bad"')

    def test_all_title_positions_and_small_heights(self):
        for position in ("outside_top", "outside_bottom", "overlay_top", "overlay_bottom"):
            for height in (0, 1, 40, 200):
                with self.subTest(position=position, height=height):
                    root = ET.fromstring(
                        generate_svg("Title", "", card_height=height, title_position=position)
                    )
                    self.assertGreaterEqual(int(root.attrib["height"]), 0)

    @patch("api.card.fetch_public_bytes", return_value=FetchedResource(PNG, "image/png"))
    def test_thumbnail_is_embedded_and_cached(self, fetch):
        url = "https://s0.wordpress.com/mshots/v1/https%3A%2F%2Fexample.com"
        first = fetch_image_as_base64(url)
        second = fetch_image_as_base64(url)
        self.assertEqual(first, second)
        self.assertEqual(fetch.call_count, 1)
        encoded = first.split(",", 1)[1]
        self.assertEqual(base64.b64decode(encoded), PNG)

    @patch("api.card.fetch_public_bytes")
    def test_thumbnail_failure_falls_back(self, fetch):
        fetch.side_effect = FetchError("invalid image")
        svg = generate_svg("Title", "https://s0.wordpress.com/failure", embed_thumbnail=True)
        self.assertIn('href="https://s0.wordpress.com/failure"', svg)


if __name__ == "__main__":
    unittest.main()
