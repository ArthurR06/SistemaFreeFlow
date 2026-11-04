import csv
import os

import joblib
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config import TEMPO_DUPLICIDADE


ARQUIVO_TREINO = "data/treino_normal.csv"
CAMINHO_MODELO_DUPLICIDADE = "app/modelo_duplicidade.joblib"


def criar_pipeline():
    return Pipeline([
        ("normalizador", StandardScaler()),
        (
            "isolation_forest",
            IsolationForest(
                n_estimators=200,
                contamination=0.05,
                random_state=42,
            ),
        ),
    ])


def carregar_dados():
    dados = []

    if not os.path.exists(ARQUIVO_TREINO):
        print(f"Arquivo não encontrado: {ARQUIVO_TREINO}")
        return np.array([])

    with open(
        ARQUIVO_TREINO,
        "r",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            try:
                intervalo = float(linha["intervalo_segundos"])
                dados.append([intervalo])

            except (ValueError, KeyError):
                continue

    return np.array(dados, dtype=float)


def treinar():
    print("")
    print("==============================")
    print("TREINAMENTO DA IA")
    print("==============================")

    dados = carregar_dados()

    print(f"Amostras carregadas: {len(dados)}")

    if len(dados) < 20:
        print("")
        print("ERRO: poucos dados para treinamento.")
        return

    modelo_duplicidade = criar_pipeline()

    print("")
    print("Treinando modelo temporal de intervalos...")

    modelo_duplicidade.fit(dados)

    joblib.dump(
        modelo_duplicidade,
        CAMINHO_MODELO_DUPLICIDADE,
    )

    print("")
    print("==============================")
    print("MODELO TREINADO COM SUCESSO!")
    print("==============================")

    print(f"Modelo temporal salvo em: {CAMINHO_MODELO_DUPLICIDADE}")

    # Testes simples
    print("")
    print("Teste do modelo:")

    for intervalo in (10, 29, 30, 120):
        predicao = modelo_duplicidade.predict(np.array([[intervalo]]))[0]
        decisao = (
            "DUPLICIDADE"
            if intervalo < TEMPO_DUPLICIDADE
            else "NORMAL"
        )
        print(
            f"Intervalo {intervalo}s: {decisao} "
            f"(Isolation Forest: {'atípico' if predicao == -1 else 'usual'})"
        )


if __name__ == "__main__":
    treinar()
