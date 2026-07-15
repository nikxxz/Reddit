import unittest

from pydantic import ValidationError

from backend.config import Settings


class ConfigValidationTests(unittest.TestCase):
    def test_invalid_port_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(app_port=0)

    def test_zero_concurrency_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(max_concurrent_downloads=0)

    def test_negative_timeout_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(media_read_timeout=-1)

    def test_invalid_thumbnail_format_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(thumbnail_format="bmp")

    def test_jpg_normalizes_to_jpeg(self):
        self.assertEqual(Settings(thumbnail_format="jpg").thumbnail_format, "jpeg")

    def test_invalid_boolean_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(debug="sometimes")


if __name__ == "__main__":
    unittest.main()
