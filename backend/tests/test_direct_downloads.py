import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from backend.services.downloads.direct import download_direct_url, validate_download_url
from backend.services.downloads.errors import DownloadError, UrlSafetyError


class FakeStream:
    def __init__(self, status_code=200, chunks=None, content_type="image/jpeg", headers=None):
        self.response = httpx.Response(
            status_code,
            headers={"content-type": content_type, **(headers or {})},
            request=httpx.Request("GET", "https://i.redd.it/example.jpg"),
        )
        self.chunks = chunks or [b"abc"]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    @property
    def headers(self):
        return self.response.headers

    def raise_for_status(self):
        self.response.raise_for_status()

    def iter_bytes(self):
        yield from self.chunks


def public_dns(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


class DirectDownloadTests(unittest.TestCase):
    def test_successful_image_download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", return_value=FakeStream(chunks=[b"image"])
            ):
                path = download_direct_url("https://i.redd.it/example.jpg", Path(tmpdir))
        self.assertEqual(path.name, "example.jpg")

    def test_timeout_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", side_effect=httpx.ReadTimeout("timed out")
            ):
                with self.assertRaises(DownloadError):
                    download_direct_url("https://i.redd.it/example.jpg", output_dir)
            self.assertFalse((output_dir / "example.jpg.part").exists())

    def test_http_404(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", return_value=FakeStream(status_code=404)
            ):
                with self.assertRaises(DownloadError):
                    download_direct_url("https://i.redd.it/missing.jpg", Path(tmpdir))

    def test_http_429_with_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams = [
                FakeStream(status_code=429, headers={"Retry-After": "0"}),
                FakeStream(chunks=[b"ok"]),
            ]
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", side_effect=streams
            ):
                path = download_direct_url("https://i.redd.it/example.jpg", Path(tmpdir))
            self.assertTrue(path.exists())

    def test_http_500_with_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams = [FakeStream(status_code=500), FakeStream(chunks=[b"ok"])]
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", side_effect=streams
            ):
                path = download_direct_url("https://i.redd.it/example.jpg", Path(tmpdir))
            self.assertTrue(path.exists())

    def test_invalid_content_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("socket.getaddrinfo", public_dns), patch(
                "httpx.stream", return_value=FakeStream(content_type="text/html")
            ):
                with self.assertRaises(DownloadError):
                    download_direct_url("https://i.redd.it/example.jpg", Path(tmpdir))

    def test_private_ip_url_rejection(self):
        with patch(
            "socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
        ):
            with self.assertRaises(UrlSafetyError):
                validate_download_url("https://i.redd.it/example.jpg")

    def test_unsupported_url_scheme_rejection(self):
        with self.assertRaises(UrlSafetyError):
            validate_download_url("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
