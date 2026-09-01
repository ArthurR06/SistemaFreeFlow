# configs do projeto
import os
from dotenv import load_dotenv

# carrega .env
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "local")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/freeflow.db")
VALOR_PASSAGEM = float(os.getenv("VALOR_PASSAGEM", "5.0"))
TEMPO_DUPLICIDADE = int(os.getenv("TEMPO_DUPLICIDADE", "60"))
TEMPO_SEM_DADOS_ALERTA = int(os.getenv("TEMPO_SEM_DADOS_ALERTA", "120"))
REFRESH_SEGUNDOS = int(os.getenv("REFRESH_SEGUNDOS", "5"))
# Área administrativa
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

CONCESSIONARIAS_ADMIN = {

    os.getenv(
        "CONCESSIONARIA_A_USER",
        "concessionaria_a"
    ): {
        "senha": os.getenv(
            "CONCESSIONARIA_A_PASSWORD",
            "admin_a"
        ),
        "id": "A",
        "nome": "Concessionária A",
        "faixas": [1]
    },

    os.getenv(
        "CONCESSIONARIA_B_USER",
        "concessionaria_b"
    ): {
        "senha": os.getenv(
            "CONCESSIONARIA_B_PASSWORD",
            "admin_b"
        ),
        "id": "B",
        "nome": "Concessionária B",
        "faixas": [2]
    }

}

# Chave usada para manter o login do admin na sessão
SESSION_SECRET = os.getenv(
    "SESSION_SECRET",
    "freeflow-admin-secret"
)