# configs do projeto
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# O arquivo local tem precedência e nunca é versionado.
load_dotenv(BASE_DIR / ".env.local")
load_dotenv(BASE_DIR / ".env")

APP_ENV = os.getenv("APP_ENV", "local")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/freeflow.db")
VALOR_PASSAGEM = float(os.getenv("VALOR_PASSAGEM", "5.0"))
VALOR_PASSAGEM_A = float(os.getenv("VALOR_PASSAGEM_A", str(VALOR_PASSAGEM)))
VALOR_PASSAGEM_B = float(os.getenv("VALOR_PASSAGEM_B", "7.5"))
TEMPO_DUPLICIDADE = int(os.getenv("TEMPO_DUPLICIDADE", "30"))
TEMPO_SEM_DADOS_ALERTA = int(os.getenv("TEMPO_SEM_DADOS_ALERTA", "120"))
REFRESH_SEGUNDOS = int(os.getenv("REFRESH_SEGUNDOS", "5"))
# Área administrativa
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ESP32_API_KEY = os.getenv("ESP32_API_KEY", "")

CONCESSIONARIAS_ADMIN = {

    "concessionaria_a": {
        "senha": os.getenv(
            "CONCESSIONARIA_A_PASSWORD",
            "admin_a"
        ),
        "id": "A",
        "nome": "ConectaVia",
        "sigla": "CV",
        "logo_url": "/static/logos/conectavia-simbolo.png",
        "valor_passagem": VALOR_PASSAGEM_A,
        "faixas": [1]
    },

    "concessionaria_b": {
        "senha": os.getenv(
            "CONCESSIONARIA_B_PASSWORD",
            "admin_b"
        ),
        "id": "B",
        "nome": "RotaLink",
        "sigla": "RL",
        "logo_url": "/static/logos/rotalink-simbolo.png",
        "valor_passagem": VALOR_PASSAGEM_B,
        "faixas": [2]
    }

}

VALORES_PASSAGEM_POR_FAIXA = {
    faixa: dados["valor_passagem"]
    for dados in CONCESSIONARIAS_ADMIN.values()
    for faixa in dados["faixas"]
}


def valor_passagem_por_faixa(faixa: int) -> float:
    return VALORES_PASSAGEM_POR_FAIXA.get(faixa, VALOR_PASSAGEM)

# Chave usada para manter o login do admin na sessão
SESSION_SECRET = os.getenv(
    "SESSION_SECRET",
    "freeflow-admin-secret"
)

COOKIE_SECURE = APP_ENV.lower() == "production"


def validar_configuracao() -> None:
    if APP_ENV.lower() != "production":
        return

    erros = []

    if DATABASE_URL.startswith("sqlite"):
        erros.append("DATABASE_URL deve apontar para o PostgreSQL")
    if SESSION_SECRET == "freeflow-admin-secret":
        erros.append("SESSION_SECRET ainda usa o valor padrão")
    if not ESP32_API_KEY:
        erros.append("ESP32_API_KEY não foi configurada")

    if erros:
        raise RuntimeError("Configuração de produção inválida: " + "; ".join(erros))


validar_configuracao()
