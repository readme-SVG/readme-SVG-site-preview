import math
import unittest

from api.validation import (
    clean_text,
    normalize_color,
    normalize_website_url,
    safe_float,
    safe_int,
)


class ValidationTests(unittest.TestCase):
    def test_numeric_defaults(self):
        for value in (None, "", "bad", "nan", "inf", "-inf", [], {}):
            self.assertEqual(safe_int(value, 7), 7)
            self.assertEqual(safe_float(value, 0.5), 0.5)
        self.assertEqual(safe_int("0", 7), 0)
        self.assertEqual(safe_int(0, 7), 0)
        self.assertTrue(math.isfinite(safe_float("1e309", 0.5)))

    def test_url_normalization(self):
        self.assertEqual(normalize_website_url("example.com/a b"), "https://example.com/a%20b")
        self.assertEqual(normalize_website_url("HTTP://EXAMPLE.COM:80"), "http://example.com/")
        self.assertEqual(normalize_website_url("https://example.com:443"), "https://example.com/")
        self.assertEqual(
            normalize_website_url("https://пример.рф"), "https://xn--e1afmkfd.xn--p1ai/"
        )
        self.assertIn("%28", normalize_website_url("https://example.com/a(b)"))
        self.assertIn("%22", normalize_website_url('https://example.com/?q="hello"'))

    def test_unsafe_or_malformed_urls(self):
        for value in (
            "",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "ftp://example.com",
            "https://user:pass@example.com",
            "https://example.com:8080",
            "https://example.com:bad",
            "https://example.com:99999",
            "https://example.com\\@127.0.0.1",
            "https://example.com/\ninvalid",
            "https://" + "a" * 2048,
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_website_url(value)

    def test_colors_and_xml_controls(self):
        self.assertEqual(normalize_color("#AbC", "#000000"), "#aabbcc")
        self.assertEqual(normalize_color("ffffff", "#000000"), "#ffffff")
        for value in ("red", "#12", "url(https://evil.test)", '#fff" onload="x', None):
            self.assertEqual(normalize_color(value, "#000000"), "#000000")
        self.assertEqual(clean_text("a\x00b\x08c\td\ne\rf"), "abc\td\ne\rf")


if __name__ == "__main__":
    unittest.main()
