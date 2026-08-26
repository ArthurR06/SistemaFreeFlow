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

# Chave usada para manter o login do admin na sessão
SESSION_SECRET = os.getenv(
    "SESSION_SECRET",
    "freeflow-admin-secret"
)