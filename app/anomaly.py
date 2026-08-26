from sqlalchemy.orm import Session
from app.models import EventoPassagem
from app.config import TEMPO_DUPLICIDADE

from datetime import datetime
from time import perf_counter

import joblib
import numpy as np


# ==========================================
# CARREGA A IA UMA ÚNICA VEZ
# ==========================================
CAMINHO_MODELO = "app/modelo_anomalia.joblib"

print("")
print("==============================")
print("CARREGANDO MODELO DE IA")
print("==============================")

MODELO_IA = joblib.load(CAMINHO_MODELO)

print("Isolation Forest carregado com sucesso.")
print("==============================")


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
        # REGRA DETERMINÍSTICA DE DUPLICIDADE
        # ======================================
        elif diferenca < TEMPO_DUPLICIDADE:

            evento.anomalia = "duplicidade"

            print("Regra temporal: DUPLICIDADE")
            print("Resultado: DUPLICIDADE")
            print("Cobrança: NÃO")

        # ======================================
        # ANÁLISE COM ISOLATION FOREST
        # ======================================
        else:

            # Converte o horário para decimal
            hora_decimal = (
                tempo_atual.hour
                + tempo_atual.minute / 60
                + tempo_atual.second / 3600
            )

            # Mesmos atributos usados no treinamento:
            # faixa, intervalo_segundos, hora_decimal
            entrada_ia = np.array([
                [
                    evento.faixa,
                    diferenca,
                    hora_decimal
                ]
            ])

            inicio_ia = perf_counter()

            resultado_ia = MODELO_IA.predict(
                entrada_ia
            )[0]

            fim_ia = perf_counter()

            tempo_ia_ms = (
                fim_ia - inicio_ia
            ) * 1000

            print(
                f"Tempo da IA: {tempo_ia_ms:.2f} ms"
            )

            if resultado_ia == -1:

                evento.anomalia = "ia_anomalia"

                print(
                    "Isolation Forest: ANOMALIA"
                )
                print("Resultado: ANOMALIA")
                print("Cobrança: NÃO")

            else:

                evento.anomalia = None

                print(
                    "Isolation Forest: NORMAL"
                )
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