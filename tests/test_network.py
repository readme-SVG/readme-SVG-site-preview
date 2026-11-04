import unittest
from typing import ClassVar
from unittest.mock import patch

from api.network import FetchError, _public_address, fetch_public_bytes


class FakeResponse:
    def __init__(self, data=b"", status=200, headers=None):
        self.data = data
        self.status = status
        self.headers = headers or {}
        self.closed = False

    def read(self, amount, decode_content=True):
        chunk, self.data = self.data[:amount], self.data[amount:]
        return chunk

    def close(self):
        self.closed = True


class FakePool:
    instances: ClassVar[list] = []

    def __init__(self, host, port, **options):
        self.host = host
        self.port = port
        self.options = options
        self.responses = []
        self.closed = False
        self.instances.append(self)

    def request(self, method, path, **kwargs):
        self.last_request = (method, path, kwargs)
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class NetworkTests(unittest.TestCase):
    def setUp(self):
        FakePool.instances = []

    def test_public_address_classification(self):
        for address in ("8.8.8.8", "1.1.1.1", "2001:4860:4860::8888", "::ffff:8.8.8.8"):
            self.assertTrue(_public_address(address), address)
        for address in (
            "127.0.0.1",
            "0.0.0.0",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "169.254.169.254",
            "100.64.0.1",
            "::1",
            "fc00::1",
            "fe80::1",
            "fec0::1",
            "::ffff:127.0.0.1",
            "64:ff9b::7f00:1",
            "2002:7f00:1::",
            "2001:0:4136:e378:8000:63bf:3fff:fdd2",
            "224.0.0.1",
        ):
            self.assertFalse(_public_address(address), address)

    @patch("api.network.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))])
    def test_dns_pinning_preserves_host_and_sni(self, resolver):
        response = FakeResponse(b"<title>Example</title>", headers={"Content-Type": "text/html"})

        def create_pool(host, port, **options):
            pool = FakePool(host, port, **options)
            pool.responses.append(response)
            return pool

        with patch("api.network.urllib3.HTTPSConnectionPool", side_effect=create_pool):
            result = fetch_public_bytes("https://example.com/test", max_bytes=1024, timeout=2)
        pool = FakePool.instances[0]
        self.assertEqual(result.data, b"<title>Example</title>")
        self.assertEqual(pool.host, "93.184.216.34")
        self.assertEqual(pool.options["server_hostname"], "example.com")
        self.assertEqual(pool.options["assert_hostname"], "example.com")
        self.assertEqual(pool.last_request[2]["headers"]["Host"], "example.com")
        self.assertTrue(response.closed)
        self.assertTrue(pool.closed)

    def test_ipv6_literal_keeps_bracketed_host_header(self):
        response = FakeResponse(b"<title>IPv6</title>", headers={"Content-Type": "text/html"})

        def create_pool(host, port, **options):
            pool = FakePool(host, port, **options)
            pool.responses.append(response)
            return pool

        with patch("api.network.urllib3.HTTPSConnectionPool", side_effect=create_pool):
            fetch_public_bytes("https://[2001:4860:4860::8888]/", max_bytes=1024, timeout=2)
        pool = FakePool.instances[0]
        self.assertEqual(pool.host, "2001:4860:4860::8888")
        self.assertEqual(pool.last_request[2]["headers"]["Host"], "[2001:4860:4860::8888]")

    @patch("api.network.socket.getaddrinfo")
    def test_mixed_public_private_dns_is_rejected(self, resolver):
        resolver.return_value = [(2, 1, 6, "", ("8.8.8.8", 80)), (2, 1, 6, "", ("127.0.0.1", 80))]
        with self.assertRaises(FetchError), patch("api.network.urllib3.HTTPConnectionPool") as pool:
            fetch_public_bytes("http://example.com", max_bytes=1024, timeout=2)
        pool.assert_not_called()

    @patch("api.network.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))])
    def test_redirect_to_private_address_is_rejected(self, resolver):
        redirect = FakeResponse(status=302, headers={"Location": "https://127.0.0.1/admin"})

        def create_pool(host, port, **options):
            pool = FakePool(host, port, **options)
            pool.responses.append(redirect)
            return pool

        with (
            patch("api.network.urllib3.HTTPSConnectionPool", side_effect=create_pool),
            self.assertRaises(FetchError),
        ):
            fetch_public_bytes("https://example.com", max_bytes=1024, timeout=2)
        self.assertEqual(len(FakePool.instances), 1)
        self.assertTrue(redirect.closed)

    @patch("api.network.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))])
    def test_read_limit_includes_unannounced_body(self, resolver):
        response = FakeResponse(b"x" * 1025, headers={"Content-Type": "text/html"})

        def create_pool(host, port, **options):
            pool = FakePool(host, port, **options)
            pool.responses.append(response)
            return pool

        with (
            patch("api.network.urllib3.HTTPConnectionPool", side_effect=create_pool),
            self.assertRaises(FetchError),
        ):
            fetch_public_bytes("http://example.com", max_bytes=1024, timeout=2)
        self.assertTrue(response.closed)

    @patch("api.network.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))])
    def test_image_content_must_be_raster(self, resolver):
        response = FakeResponse(b"<svg onload='alert(1)'/>", headers={"Content-Type": "image/png"})

        def create_pool(host, port, **options):
            pool = FakePool(host, port, **options)
            pool.responses.append(response)
            return pool

        with (
            patch("api.network.urllib3.HTTPSConnectionPool", side_effect=create_pool),
            self.assertRaises(FetchError),
        ):
            fetch_public_bytes(
                "https://example.com/image.png", max_bytes=1024, timeout=2, raster_only=True
            )


if __name__ == "__main__":
    unittest.main()
