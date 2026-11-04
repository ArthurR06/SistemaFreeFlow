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
CAMINHO_MODELO_DUPLICIDADE = Path(__file__).resolve().with_name(
    "modelo_duplicidade.joblib"
)

print("")
print("==============================")
print("CARREGANDO MODELO DE IA")
print("==============================")

MODELO_DUPLICIDADE = joblib.load(CAMINHO_MODELO_DUPLICIDADE)

print("Modelo temporal Isolation Forest carregado com sucesso.")
print("==============================")


def classificar_com_ia(
    intervalo_segundos: float,
):
    """Classifica somente duplicidades temporais, sem usar o horário.

    O Isolation Forest temporal avalia o intervalo entre passagens. A janela
    determinística estritamente inferior a 30 segundos é a regra operacional
    final: eventos dentro dela são duplicidades mesmo se o modelo produzir um
    falso negativo; eventos em 30 segundos ou mais não são bloqueados por IA.
    """
    if intervalo_segundos >= TEMPO_DUPLICIDADE:
        return {
            "classificacao": None,
            "predicao_duplicidade": None,
            "score_duplicidade": None,
            "origem_classificacao": "fora_janela",
            "tempo_ia_ms": 0.0,
        }

    entrada_temporal = np.array([[intervalo_segundos]], dtype=float)

    inicio_ia = perf_counter()
    predicao_duplicidade = int(
        MODELO_DUPLICIDADE.predict(entrada_temporal)[0]
    )
    score_duplicidade = float(
        MODELO_DUPLICIDADE.decision_function(entrada_temporal)[0]
    )
    tempo_ia_ms = (perf_counter() - inicio_ia) * 1000

    if intervalo_segundos < TEMPO_DUPLICIDADE:
        classificacao = "duplicidade"
        origem_classificacao = (
            "ia_temporal"
            if predicao_duplicidade == -1
            else "salvaguarda_temporal"
        )
    else:
        classificacao = None
        origem_classificacao = "fora_janela"

    return {
        "classificacao": classificacao,
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

    # Guarda a última passagem conhecida de cada veículo, incluindo eventos
    # já processados. Sem essa consulta, uma chamada por leitura trataria cada
    # evento como primeira passagem e não aplicaria a janela de duplicidade.
    ultimo_evento_por_veiculo = {}

    veiculos_pendentes = {evento.id_veiculo for evento in eventos}
    for veiculo in veiculos_pendentes:
        historico = (
            db.query(EventoPassagem)
            .filter(
                EventoPassagem.id_veiculo == veiculo,
                EventoPassagem.processado == 1,
            )
            .order_by(EventoPassagem.id.desc())
            .all()
        )

        for evento_anterior in historico:
            try:
                ultimo_evento_por_veiculo[veiculo] = datetime.fromisoformat(
                    evento_anterior.timestamp_evento
                )
                break
            except ValueError:
                continue

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

            resultado = classificar_com_ia(
                intervalo_segundos=diferenca,
            )

            evento.anomalia = resultado["classificacao"]

            if resultado["predicao_duplicidade"] is None:
                print("IA temporal: não aplicada (intervalo fora da janela)")
            else:
                print(
                    "Isolation Forest temporal:",
                    (
                        "ANOMALIA"
                        if resultado["predicao_duplicidade"] == -1
                        else "NORMAL"
                    ),
                )
                print(f"Score temporal: {resultado['score_duplicidade']:.6f}")
            print(f"Origem da decisão: {resultado['origem_classificacao']}")
            print(f"Tempo da IA: {resultado['tempo_ia_ms']:.2f} ms")

            if evento.anomalia == "duplicidade":
                print(
                    "Categoria operacional: DUPLICIDADE "
                    f"(IA temporal + intervalo inferior a {TEMPO_DUPLICIDADE}s)"
                )
                print("Resultado: DUPLICIDADE")
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
