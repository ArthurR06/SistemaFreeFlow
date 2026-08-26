#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <time.h>
#include <WiFiClient.h>
#include "secrets.h"

// ==========================================
// WI-FI
// ==========================================

const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ==========================================
// SERVIDOR FASTAPI
// ==========================================

// IP atual do notebook
const char* URL_EVENTO =
  "http://10.28.245.62:8002/evento";

// ==========================================
// MAC DOS DOIS ESP32
// ==========================================

// ESP32 antigo = Faixa 1
const char* MAC_FAIXA_1 =
  "8C:94:DF:4C:E9:B4";

// ESP32 novo = Faixa 2
const char* MAC_FAIXA_2 =
  "20:9B:A9:8B:91:74";

// ==========================================
// RFID RC522
// ==========================================

#define SS_PIN 5
#define RST_PIN 2

#define SCK_PIN 18
#define MISO_PIN 19
#define MOSI_PIN 23

MFRC522 rfid(SS_PIN, RST_PIN);

// ==========================================
// CONFIGURAÇÃO DA FAIXA
// ==========================================

int faixa = 0;

String sensorId = "";

String origem = "esp32_rfid";

// Evita múltiplas leituras locais
// da mesma tag em sequência
String ultimaTag = "";

unsigned long ultimoEnvio = 0;

const unsigned long intervaloEntreLeituras = 3000;


// ==========================================
// IDENTIFICA A FAIXA PELO MAC DO ESP32
// ==========================================

void identificarFaixa() {

  WiFi.mode(WIFI_STA);

  delay(200);

  String mac = WiFi.macAddress();

  mac.toUpperCase();

  Serial.println("");
  Serial.println("==============================");

  Serial.print("MAC deste ESP32: ");
  Serial.println(mac);

  if (mac == MAC_FAIXA_1) {

    faixa = 1;
    sensorId = "rfid_faixa_1";

  }

  else if (mac == MAC_FAIXA_2) {

    faixa = 2;
    sensorId = "rfid_faixa_2";

  }

  else {

    faixa = 0;
    sensorId = "esp32_nao_cadastrado";

  }

  Serial.print("Faixa identificada: ");
  Serial.println(faixa);

  Serial.print("Sensor: ");
  Serial.println(sensorId);

  Serial.println("==============================");
}


// ==========================================
// DATA / HORA
// ==========================================

String pegarTimestamp() {

  struct tm timeinfo;

  if (!getLocalTime(&timeinfo)) {

    Serial.println(
      "ERRO: horario NTP indisponivel."
    );

    return "2026-01-01T00:00:00";
  }

  char buffer[25];

  strftime(
    buffer,
    sizeof(buffer),
    "%Y-%m-%dT%H:%M:%S",
    &timeinfo
  );

  return String(buffer);
}


// ==========================================
// CONVERTE UID RFID PARA STRING
// ==========================================

String lerUID() {

  String uid = "";

  for (
    byte i = 0;
    i < rfid.uid.size;
    i++
  ) {

    if (
      rfid.uid.uidByte[i] < 0x10
    ) {

      uid += "0";

    }

    uid += String(
      rfid.uid.uidByte[i],
      HEX
    );
  }

  uid.toUpperCase();

  return uid;
}


// ==========================================
// CONECTA AO WI-FI
// ==========================================

void conectarWiFi() {

  Serial.println("");
  Serial.println("Conectando ao Wi-Fi...");

  WiFi.begin(
    ssid,
    password
  );

  while (
    WiFi.status() != WL_CONNECTED
  ) {

    delay(500);
    Serial.print(".");
  }

  Serial.println("");

  Serial.println(
    "Wi-Fi conectado!"
  );

  Serial.print(
    "IP deste ESP32: "
  );

  Serial.println(
    WiFi.localIP()
  );
}


// ==========================================
// ENVIA EVENTO PARA O FASTAPI
// ==========================================

void enviarEvento(String uid) {

  if (
    WiFi.status() != WL_CONNECTED
  ) {

    Serial.println(
      "Wi-Fi desconectado!"
    );

    return;
  }

  if (faixa == 0) {

    Serial.println(
      "ERRO: ESP32 nao cadastrado."
    );

    return;
  }


  WiFiClient client;

  HTTPClient http;


  String timestamp =
    pegarTimestamp();


  String json = "{";

  json += "\"id_veiculo\":\"";
  json += uid;
  json += "\",";

  json += "\"faixa\":";
  json += String(faixa);
  json += ",";

  json += "\"timestamp_evento\":\"";
  json += timestamp;
  json += "\",";

  json += "\"sensor_id\":\"";
  json += sensorId;
  json += "\",";

  json += "\"origem\":\"";
  json += origem;
  json += "\"";

  json += "}";


  Serial.println("");
  Serial.println("==============================");
  Serial.println("NOVA PASSAGEM");
  Serial.println("==============================");

  Serial.print("Faixa: ");
  Serial.println(faixa);

  Serial.print("Sensor: ");
  Serial.println(sensorId);

  Serial.print("UID: ");
  Serial.println(uid);

  Serial.print("Horario: ");
  Serial.println(timestamp);

  Serial.println("");

  Serial.println(
    "Enviando para FastAPI..."
  );


  http.begin(
    client,
    URL_EVENTO
  );


  http.addHeader(
    "Content-Type",
    "application/json"
  );


  int codigoResposta =
    http.POST(json);


  Serial.print("HTTP: ");
  Serial.println(codigoResposta);


  if (
    codigoResposta > 0
  ) {

    Serial.println("");

    Serial.println(
      "Resposta do FastAPI:"
    );

    Serial.println(
      http.getString()
    );

  }

  else {

    Serial.println("");

    Serial.print(
      "ERRO HTTP: "
    );

    Serial.println(
      http.errorToString(
        codigoResposta
      )
    );

  }


  http.end();

  Serial.println("==============================");
}


// ==========================================
// SETUP
// ==========================================

void setup() {

  Serial.begin(115200);

  delay(1500);


  // ========================================
  // IDENTIFICA ESP32
  // ========================================

  identificarFaixa();


  Serial.println("");
  Serial.println("==============================");
  Serial.println("       SISTEMA FREEFLOW");
  Serial.println("==============================");


  // ========================================
  // INICIALIZA SPI + RFID
  // ========================================

  SPI.begin(
    SCK_PIN,
    MISO_PIN,
    MOSI_PIN,
    SS_PIN
  );


  rfid.PCD_Init();


  delay(100);


  Serial.println("");

  Serial.println(
    "RFID RC522 inicializado."
  );

  Serial.println(
    "Versao do leitor:"
  );

  rfid.PCD_DumpVersionToSerial();


  // ========================================
  // WI-FI
  // ========================================

  conectarWiFi();


  // ========================================
  // HORÁRIO BRASIL UTC-3
  // ========================================

  configTime(
    -3 * 3600,
    0,
    "pool.ntp.org",
    "time.nist.gov"
  );


  delay(1000);


  Serial.println("");
  Serial.println("==============================");


  if (faixa == 1) {

    Serial.println(
      "FAIXA 1 PRONTA"
    );

  }

  else if (faixa == 2) {

    Serial.println(
      "FAIXA 2 PRONTA"
    );

  }

  else {

    Serial.println(
      "ESP32 NAO CADASTRADO!"
    );

  }


  Serial.println(
    "Aproxime uma tag RFID."
  );

  Serial.println("==============================");
}


// ==========================================
// LOOP PRINCIPAL
// ==========================================

void loop() {

  // ========================================
  // RECONECTA WI-FI
  // ========================================

  if (
    WiFi.status() != WL_CONNECTED
  ) {

    Serial.println(
      "Wi-Fi caiu. Reconectando..."
    );

    WiFi.disconnect();

    conectarWiFi();

  }


  // ========================================
  // PROCURA TAG RFID
  // ========================================

  if (
    !rfid.PICC_IsNewCardPresent()
  ) {

    delay(20);

    return;
  }


  if (
    !rfid.PICC_ReadCardSerial()
  ) {

    delay(20);

    return;
  }


  String uidLido =
    lerUID();


  unsigned long agora =
    millis();


  Serial.println("");

  Serial.print(
    "Tag detectada na FAIXA "
  );

  Serial.print(
    faixa
  );

  Serial.print(
    ": "
  );

  Serial.println(
    uidLido
  );


  // ========================================
  // EVITA REPETIÇÃO LOCAL MUITO RÁPIDA
  // ========================================

  if (
    uidLido == ultimaTag &&
    agora - ultimoEnvio <
      intervaloEntreLeituras
  ) {

    Serial.println(
      "Leitura repetida local ignorada."
    );


    rfid.PICC_HaltA();

    rfid.PCD_StopCrypto1();

    return;
  }


  ultimaTag =
    uidLido;


  ultimoEnvio =
    agora;


  // ========================================
  // ENVIA PARA O BACKEND
  // ========================================

  enviarEvento(
    uidLido
  );


  // ========================================
  // FINALIZA RFID
  // ========================================

  rfid.PICC_HaltA();

  rfid.PCD_StopCrypto1();


  delay(20);
}