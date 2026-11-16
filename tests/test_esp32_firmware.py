import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class FirmwareESP32Test(unittest.TestCase):
    def test_firmware_usa_configuracao_local_ignorada(self):
        firmware = (
            BASE_DIR / "scripts" / "esp32" / "esp32.ino"
        ).read_text(encoding="utf-8")
        exemplo = (
            BASE_DIR / "scripts" / "esp32" / "secrets.example.h"
        ).read_text(encoding="utf-8")
        gitignore = (BASE_DIR / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("const char* ssid = WIFI_SSID;", firmware)
        self.assertIn("const char* password = WIFI_PASSWORD;", firmware)
        self.assertIn(
            "const char* URL_EVENTO = FREEFLOW_API_URL;",
            firmware,
        )
        self.assertNotIn("172.20.10.5", firmware)
        self.assertIn("scripts/esp32/secrets.h", gitignore)
        self.assertIn("#define WIFI_SSID", exemplo)
        self.assertIn("#define WIFI_PASSWORD", exemplo)
        self.assertIn("#define FREEFLOW_API_KEY", exemplo)
        self.assertIn("#define FREEFLOW_API_URL", exemplo)

    def test_firmware_envia_evento_para_api_https_com_chave(self):
        firmware = (
            BASE_DIR / "scripts" / "esp32" / "esp32.ino"
        ).read_text(encoding="utf-8")
        exemplo = (
            BASE_DIR / "scripts" / "esp32" / "secrets.example.h"
        ).read_text(encoding="utf-8")

        self.assertIn("#include <WiFiClientSecure.h>", firmware)
        self.assertIn('http.addHeader(\n    "X-API-Key",', firmware)
        self.assertIn(
            "https://sistema-free-flow.vercel.app/evento",
            exemplo,
        )


if __name__ == "__main__":
    unittest.main()
