import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class FirmwareESP32Test(unittest.TestCase):
    def test_firmware_suporta_endpoint_https_da_vercel(self):
        firmware = (
            BASE_DIR / "scripts" / "esp32" / "esp32.ino"
        ).read_text(encoding="utf-8")
        exemplo = (
            BASE_DIR / "scripts" / "esp32" / "secrets.example.h"
        ).read_text(encoding="utf-8")

        self.assertIn("#include <WiFiClientSecure.h>", firmware)
        self.assertIn("clientHttps.setInsecure();", firmware)
        self.assertIn('http.addHeader(\n    "X-API-Key",', firmware)
        self.assertIn(
            "https://sistema-free-flow.vercel.app/evento",
            exemplo,
        )


if __name__ == "__main__":
    unittest.main()
