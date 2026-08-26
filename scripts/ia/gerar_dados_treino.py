import csv
import os
import random

from app.config import TEMPO_DUPLICIDADE


ARQUIVO = "data/treino_normal.csv"
QUANTIDADE = 500


def gerar_dados():

    os.makedirs("data", exist_ok=True)

    dados = []

    for _ in range(QUANTIDADE):

        # Faixa 1 ou 2
        faixa = random.choice([1, 2])

        # Como estamos gerando comportamento NORMAL,
        # o intervalo fica acima do limite de duplicidade
        intervalo = random.uniform(
            TEMPO_DUPLICIDADE + 5,
            TEMPO_DUPLICIDADE + 180
        )

        # Simula passagens durante o dia
        hora_decimal = random.uniform(6, 22)

        dados.append([
            faixa,
            round(intervalo, 2),
            round(hora_decimal, 2)
        ])

    with open(
        ARQUIVO,
        "w",
        newline="",
        encoding="utf-8"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "faixa",
            "intervalo_segundos",
            "hora_decimal"
        ])

        escritor.writerows(dados)

    print("")
    print("==============================")
    print("DADOS DE TREINAMENTO GERADOS")
    print("==============================")
    print(f"Quantidade: {QUANTIDADE}")
    print(f"Arquivo: {ARQUIVO}")
    print("==============================")


if __name__ == "__main__":
    gerar_dados()