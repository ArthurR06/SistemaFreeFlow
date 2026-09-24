"""Executa cenários reproduzíveis do módulo de Inteligência Artificial."""

from app.anomaly import MODELO_IA, classificar_com_ia
from app.config import TEMPO_DUPLICIDADE


CASOS = [
    {
        "nome": "Comportamento normal",
        "faixa": 1,
        "intervalo": 120,
        "hora": 14,
        "esperado": None,
        "cobranca": "SIM",
    },
    {
        "nome": "Repetição em 10 segundos",
        "faixa": 1,
        "intervalo": 10,
        "hora": 14,
        "esperado": "duplicidade",
        "cobranca": "NÃO",
    },
    {
        "nome": "Repetição em 29 segundos",
        "faixa": 2,
        "intervalo": 29,
        "hora": 12,
        "esperado": "duplicidade",
        "cobranca": "NÃO",
    },
    {
        "nome": "Comportamento atípico",
        "faixa": 2,
        "intervalo": 120,
        "hora": 2,
        "esperado": "ia_anomalia",
        "cobranca": "NÃO",
    },
]


def executar():
    print("")
    print("=" * 66)
    print("TESTES DO MÓDULO DE IA - ISOLATION FOREST")
    print("=" * 66)
    print(f"Modelo carregado: {type(MODELO_IA).__name__}")
    print(f"Janela de duplicidade: intervalo < {TEMPO_DUPLICIDADE}s")
    print("")

    falhas = []
    resultados = []

    for indice, caso in enumerate(CASOS, start=1):
        resultado = classificar_com_ia(
            faixa=caso["faixa"],
            intervalo_segundos=caso["intervalo"],
            hora_decimal=caso["hora"],
        )
        obtido = resultado["classificacao"]
        status = "APROVADO" if obtido == caso["esperado"] else "FALHOU"
        nome_resultado = obtido or "normal"
        nome_esperado = caso["esperado"] or "normal"

        resultados.append({**caso, **resultado, "status": status})

        print(f"CT-IA-{indice:02d} | {status}")
        print(f"Cenário: {caso['nome']}")
        print(
            "Entrada: "
            f"faixa={caso['faixa']}, "
            f"intervalo={caso['intervalo']}s, "
            f"hora={caso['hora']}h"
        )
        print(
            "Modelo comportamental: "
            f"{'ANOMALIA' if resultado['predicao'] == -1 else 'NORMAL'} "
            f"| score={resultado['score']:.6f}"
        )
        print(
            "Modelo temporal: "
            f"{'ANOMALIA' if resultado['predicao_duplicidade'] == -1 else 'NORMAL'} "
            f"| score={resultado['score_duplicidade']:.6f}"
        )
        print(
            f"Classificação: {nome_resultado} "
            f"| Esperado: {nome_esperado} "
            f"| Cobrança: {caso['cobranca']}"
        )
        print("")

        if status != "APROVADO":
            falhas.append(caso["nome"])

    print("=" * 66)
    print(f"RESULTADO: {len(CASOS) - len(falhas)}/{len(CASOS)} testes aprovados")
    print("=" * 66)

    if falhas:
        raise SystemExit("Falharam: " + ", ".join(falhas))

    return resultados


if __name__ == "__main__":
    executar()
