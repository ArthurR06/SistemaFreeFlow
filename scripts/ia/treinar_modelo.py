import csv
import os

import joblib
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ARQUIVO_TREINO = "data/treino_normal.csv"
CAMINHO_MODELO = "app/modelo_anomalia.joblib"
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
                faixa = float(linha["faixa"])
                intervalo = float(linha["intervalo_segundos"])
                hora = float(linha["hora_decimal"])

                dados.append([
                    faixa,
                    intervalo,
                    hora
                ])

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

    modelo = criar_pipeline()
    modelo_duplicidade = criar_pipeline()

    print("")
    print("Treinando modelo comportamental...")

    modelo.fit(dados)
    modelo_duplicidade.fit(dados[:, 1].reshape(-1, 1))

    joblib.dump(
        modelo,
        CAMINHO_MODELO
    )
    joblib.dump(
        modelo_duplicidade,
        CAMINHO_MODELO_DUPLICIDADE,
    )

    print("")
    print("==============================")
    print("MODELOS TREINADOS COM SUCESSO!")
    print("==============================")

    print(f"Modelo salvo em: {CAMINHO_MODELO}")
    print(f"Modelo temporal salvo em: {CAMINHO_MODELO_DUPLICIDADE}")

    # Testes simples
    print("")
    print("Teste do modelo:")

    normal = np.array([
        [1, 120, 14]
    ])

    suspeito = np.array([
        [2, 120, 2]
    ])
    duplicidade = np.array([[29]])

    resultado_normal = modelo.predict(normal)[0]
    resultado_suspeito = modelo.predict(suspeito)[0]
    resultado_duplicidade = modelo_duplicidade.predict(duplicidade)[0]

    print(
        "Evento normal:",
        "NORMAL" if resultado_normal == 1 else "ANOMALIA"
    )

    print(
        "Evento fora do padrão:",
        "NORMAL" if resultado_suspeito == 1 else "ANOMALIA"
    )
    print(
        "Intervalo de duplicidade:",
        "NORMAL" if resultado_duplicidade == 1 else "ANOMALIA",
    )


if __name__ == "__main__":
    treinar()
