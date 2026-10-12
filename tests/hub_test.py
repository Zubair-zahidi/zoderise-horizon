import unittest

from zoderise.hub import normalize_hub_url, qr_png


class HubAddressTests(unittest.TestCase):
    def test_private_lan_http_is_allowed(self):
        self.assertEqual(normalize_hub_url(" http://192.168.1.20:8501/ "), "http://192.168.1.20:8501")

    def test_public_address_requires_https(self):
        with self.assertRaises(ValueError):
            normalize_hub_url("http://example.com")
        self.assertEqual(normalize_hub_url("https://ai.example.com"), "https://ai.example.com")

    def test_credentials_and_query_are_rejected(self):
        for value in ["http://user:pass@192.168.1.2:8501", "https://example.com/?token=secret"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_hub_url(value)

    def test_qr_is_png(self):
        image = qr_png("http://192.168.1.20:8501")
        self.assertIsNotNone(image)
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
