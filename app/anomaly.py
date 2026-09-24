from sqlalchemy.orm import Session
from app.models import EventoPassagem
from app.config import TEMPO_DUPLICIDADE

from datetime import datetime
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np


# ==========================================
# CARREGA A IA UMA ÚNICA VEZ
# ==========================================
CAMINHO_MODELO = Path(__file__).resolve().with_name(
    "modelo_anomalia.joblib"
)
CAMINHO_MODELO_DUPLICIDADE = Path(__file__).resolve().with_name(
    "modelo_duplicidade.joblib"
)

print("")
print("==============================")
print("CARREGANDO MODELO DE IA")
print("==============================")

MODELO_IA = joblib.load(CAMINHO_MODELO)
MODELO_DUPLICIDADE = joblib.load(CAMINHO_MODELO_DUPLICIDADE)

print("Modelos Isolation Forest carregados com sucesso.")
print("==============================")


def classificar_com_ia(
    faixa: int,
    intervalo_segundos: float,
    hora_decimal: float,
):
    """Classifica um evento com IA e aplica a categoria operacional.

    Dois modelos Isolation Forest analisam as passagens com histórico. O
    primeiro avalia o comportamento geral e o segundo é especializado no
    intervalo temporal. A janela dá o nome ``duplicidade`` à anomalia temporal
    e também funciona como proteção contra cobrança indevida caso o modelo
    experimental produza um falso negativo.
    """
    entrada_ia = np.array(
        [[faixa, intervalo_segundos, hora_decimal]],
        dtype=float,
    )

    entrada_temporal = np.array([[intervalo_segundos]], dtype=float)

    inicio_ia = perf_counter()
    predicao = int(MODELO_IA.predict(entrada_ia)[0])
    score = float(MODELO_IA.decision_function(entrada_ia)[0])
    predicao_duplicidade = int(
        MODELO_DUPLICIDADE.predict(entrada_temporal)[0]
    )
    score_duplicidade = float(
        MODELO_DUPLICIDADE.decision_function(entrada_temporal)[0]
    )
    tempo_ia_ms = (perf_counter() - inicio_ia) * 1000

    if (
        intervalo_segundos < TEMPO_DUPLICIDADE
        and predicao_duplicidade == -1
    ):
        classificacao = "duplicidade"
        origem_classificacao = "ia_temporal"
    elif intervalo_segundos < TEMPO_DUPLICIDADE:
        # Salvaguarda financeira contra um falso negativo do modelo temporal.
        classificacao = "duplicidade"
        origem_classificacao = "salvaguarda_temporal"
    elif predicao == -1:
        classificacao = "ia_anomalia"
        origem_classificacao = "ia_comportamental"
    else:
        classificacao = None
        origem_classificacao = "ia_comportamental"

    return {
        "classificacao": classificacao,
        "predicao": predicao,
        "score": score,
        "predicao_duplicidade": predicao_duplicidade,
        "score_duplicidade": score_duplicidade,
        "origem_classificacao": origem_classificacao,
        "tempo_ia_ms": tempo_ia_ms,
    }


# ==========================================
# ANALISA EVENTOS
# ==========================================
def analisar_eventos(db: Session):

    inicio_analise = perf_counter()

    # Busca somente eventos ainda não processados
    eventos = (
        db.query(EventoPassagem)
        .filter(EventoPassagem.processado == 0)
        .order_by(EventoPassagem.id.asc())
        .all()
    )

    print("")
    print("==============================")
    print("ANÁLISE DE EVENTOS")
    print("==============================")
    print(f"Eventos novos: {len(eventos)}")

    # Guarda a última passagem conhecida
    # de cada veículo, sem considerar a faixa
    ultimo_evento_por_veiculo = {}

    # ==========================================
    # HISTÓRICO JÁ PROCESSADO
    # ==========================================
    historico = (
        db.query(EventoPassagem)
        .filter(EventoPassagem.processado == 1)
        .order_by(EventoPassagem.id.asc())
        .all()
    )

    for evento in historico:

        try:
            timestamp = datetime.fromisoformat(
                evento.timestamp_evento
            )

        except ValueError:
            continue

        veiculo = evento.id_veiculo

        if (
            veiculo not in ultimo_evento_por_veiculo
            or timestamp > ultimo_evento_por_veiculo[veiculo]
        ):
            ultimo_evento_por_veiculo[veiculo] = timestamp

    # ==========================================
    # ANALISA EVENTOS NOVOS
    # ==========================================
    for evento in eventos:

        veiculo = evento.id_veiculo

        print("")
        print("------------------------------")
        print(f"Evento ID: {evento.id}")
        print(f"Veículo: {evento.id_veiculo}")
        print(f"Faixa: {evento.faixa}")

        # ======================================
        # VALIDA TIMESTAMP
        # ======================================
        try:
            tempo_atual = datetime.fromisoformat(
                evento.timestamp_evento
            )

        except ValueError:

            evento.anomalia = "timestamp_invalido"
            evento.processado = 1

            print("Resultado: TIMESTAMP INVÁLIDO")
            print("Cobrança: NÃO")

            continue

        # ======================================
        # PRIMEIRA PASSAGEM CONHECIDA
        # ======================================
        if veiculo not in ultimo_evento_por_veiculo:

            evento.anomalia = None
            evento.processado = 1

            ultimo_evento_por_veiculo[veiculo] = tempo_atual

            print(
                "Primeira passagem conhecida deste veículo."
            )
            print(
                "IA: aguardando histórico para calcular intervalo."
            )
            print("Resultado: NORMAL")
            print("Cobrança: SIM")

            continue

        # ======================================
        # CALCULA INTERVALO
        # ======================================
        tempo_anterior = ultimo_evento_por_veiculo[veiculo]

        diferenca = (
            tempo_atual - tempo_anterior
        ).total_seconds()

        print(
            f"Intervalo desde última passagem: {diferenca:.2f}s"
        )

        # ======================================
        # EVENTO FORA DE ORDEM
        # ======================================
        if diferenca < 0:

            evento.anomalia = "timestamp_invalido"

            print("Resultado: TIMESTAMP INVÁLIDO")
            print("Cobrança: NÃO")

        # ======================================
        # ANÁLISE COM ISOLATION FOREST
        # ======================================
        else:

            # Converte o horário para decimal.
            hora_decimal = (
                tempo_atual.hour
                + tempo_atual.minute / 60
                + tempo_atual.second / 3600
            )

            resultado = classificar_com_ia(
                faixa=evento.faixa,
                intervalo_segundos=diferenca,
                hora_decimal=hora_decimal,
            )

            evento.anomalia = resultado["classificacao"]

            print(
                "Isolation Forest comportamental:",
                "ANOMALIA" if resultado["predicao"] == -1 else "NORMAL",
            )
            print(f"Score comportamental: {resultado['score']:.6f}")
            print(
                "Isolation Forest temporal:",
                (
                    "ANOMALIA"
                    if resultado["predicao_duplicidade"] == -1
                    else "NORMAL"
                ),
            )
            print(f"Score temporal: {resultado['score_duplicidade']:.6f}")
            print(f"Tempo da IA: {resultado['tempo_ia_ms']:.2f} ms")

            if evento.anomalia == "duplicidade":
                print(
                    "Categoria operacional: DUPLICIDADE "
                    f"(IA temporal + intervalo inferior a {TEMPO_DUPLICIDADE}s)"
                )
                print("Resultado: DUPLICIDADE")
                print("Cobrança: NÃO")
            elif evento.anomalia == "ia_anomalia":
                print("Resultado: ANOMALIA")
                print("Cobrança: NÃO")
            else:
                print("Resultado: NORMAL")
                print("Cobrança: SIM")

        # ======================================
        # ATUALIZA ÚLTIMA PASSAGEM
        # ======================================
        if diferenca >= 0:

            ultimo_evento_por_veiculo[
                veiculo
            ] = tempo_atual

        evento.processado = 1

    # ==========================================
    # SALVA ALTERAÇÕES
    # ==========================================
    db.commit()

    # ==========================================
    # TEMPO TOTAL
    # ==========================================
    fim_analise = perf_counter()

    tempo_total_ms = (
        fim_analise - inicio_analise
    ) * 1000

    print("")
    print("==============================")
    print("ANÁLISE FINALIZADA")
    print(
        f"Tempo total da análise: {tempo_total_ms:.2f} ms"
    )
    print("==============================")
