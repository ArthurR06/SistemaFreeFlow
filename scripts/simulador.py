# simulador de eventos
import requests
from datetime import datetime, timedelta
import time


URL_EVENTO = "http://127.0.0.1:8000/evento"
URL_ANALISAR = "http://127.0.0.1:8000/analisar"

agora = datetime.now()

eventos = [
    {
        "id_veiculo": "12345-AB3",
        "faixa": 1,
        "timestamp_evento": agora.isoformat(timespec="seconds"),
        "sensor_id": "rfid_faixa_1",
        "origem": "simulador"
    },
    {
        "id_veiculo": "67890-CDE",
        "faixa": 2,
        "timestamp_evento": (agora + timedelta(seconds=1)).isoformat(timespec="seconds"),
        "sensor_id": "rfid_faixa_2",
        "origem": "simulador"
    },
    {
        "id_veiculo": "11223-FGH",
        "faixa": 1,
        "timestamp_evento": (agora + timedelta(seconds=2)).isoformat(timespec="seconds"),
        "sensor_id": "rfid_faixa_1",
        "origem": "simulador"
    },
    {
        "id_veiculo": "33444-IJK",
        "faixa": 2,
        "timestamp_evento": (agora + timedelta(seconds=3)).isoformat(timespec="seconds"),
        "sensor_id": "rfid_faixa_2",
        "origem": "simulador"
    },
    {
        "id_veiculo": "11223-FGH",
        "faixa": 1,
        "timestamp_evento": (agora + timedelta(seconds=4)).isoformat(timespec="seconds"),
        "sensor_id": "rfid_faixa_1",
        "origem": "simulador"
    }
]

for evento in eventos:
    resposta = requests.post(URL_EVENTO, json=evento)
    print("Evento enviado:", resposta.status_code, resposta.json())
    time.sleep(1)

resposta_analise = requests.post(URL_ANALISAR)
print("Análise:", resposta_analise.status_code, resposta_analise.json())
