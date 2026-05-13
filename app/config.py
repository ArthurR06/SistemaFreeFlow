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
