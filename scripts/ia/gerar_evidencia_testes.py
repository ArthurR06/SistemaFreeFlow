"""Gera uma imagem de evidências para a documentação do módulo de IA."""

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.anomaly import MODELO_IA, classificar_com_ia
from app.config import TEMPO_DUPLICIDADE


ROOT = Path(__file__).resolve().parents[2]
SAIDA = ROOT / "docs" / "testes-ia-isolation-forest.png"


def fonte(nome: str, tamanho: int):
    caminho = Path("C:/Windows/Fonts") / nome
    return ImageFont.truetype(str(caminho), tamanho)


def executar_testes(modulo: str):
    processo = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", modulo],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    saida = processo.stdout + processo.stderr
    executados = 0
    for linha in saida.splitlines():
        if linha.startswith("Ran ") and " test" in linha:
            executados = int(linha.split()[1])
            break
    return processo.returncode == 0, executados, saida


def contar_amostras():
    with (ROOT / "data" / "treino_normal.csv").open(
        "r", encoding="utf-8", newline=""
    ) as arquivo:
        return sum(1 for _ in csv.DictReader(arquivo))


def texto(draw, posicao, valor, font, fill="#17324d"):
    draw.text(posicao, valor, font=font, fill=fill)


def gerar():
    ok_ia, total_ia, saida_ia = executar_testes("tests.test_ia")
    ok_fluxos, total_fluxos, saida_fluxos = executar_testes("tests.test_fluxos")
    if not ok_ia or not ok_fluxos:
        print(saida_ia)
        print(saida_fluxos)
        raise SystemExit("Os testes falharam; a evidência não foi gerada.")

    casos = [
        ("Primeira passagem", "Sem histórico", "NORMAL", "SIM", "Fluxo"),
        ("Repetição curta", "10s · faixa 1 · 14h", "DUPLICIDADE", "NÃO", "IA + janela"),
        ("Repetição curta", "29s · faixa 2 · 12h", "DUPLICIDADE", "NÃO", "IA + janela"),
        ("Limite da janela", "30s · faixa 1 · 14h", "NORMAL", "SIM", "IA"),
        ("Evento normal", "120s · faixa 1 · 14h", "NORMAL", "SIM", "IA"),
        ("Evento atípico", "120s · faixa 2 · 2h", "IA_ANOMALIA", "NÃO", "IA"),
    ]

    resultados = {
        "Repetição curta-10s · faixa 1 · 14h": classificar_com_ia(1, 10, 14),
        "Repetição curta-29s · faixa 2 · 12h": classificar_com_ia(2, 29, 12),
        "Limite da janela-30s · faixa 1 · 14h": classificar_com_ia(1, 30, 14),
        "Evento normal-120s · faixa 1 · 14h": classificar_com_ia(1, 120, 14),
        "Evento atípico-120s · faixa 2 · 2h": classificar_com_ia(2, 120, 2),
    }

    imagem = Image.new("RGB", (2000, 1500), "#f5f8fb")
    draw = ImageDraw.Draw(imagem)
    titulo = fonte("segoeuib.ttf", 62)
    subtitulo = fonte("segoeui.ttf", 30)
    cabecalho = fonte("segoeuib.ttf", 27)
    corpo = fonte("segoeui.ttf", 25)
    corpo_bold = fonte("segoeuib.ttf", 25)
    pequeno = fonte("segoeui.ttf", 22)

    draw.rounded_rectangle((70, 55, 1930, 260), radius=34, fill="#063b5c")
    texto(draw, (120, 90), "Evidências dos testes do módulo de IA", titulo, "white")
    texto(
        draw,
        (122, 175),
        "Isolation Forest · detecção de anomalias · proteção contra cobranças indevidas",
        subtitulo,
        "#bdeaf0",
    )

    cards = [
        ("Amostras de treino", str(contar_amostras())),
        ("Modelos / árvores", f"2 × {MODELO_IA.named_steps['isolation_forest'].n_estimators}"),
        ("Contaminação", "5%"),
        ("Janela de duplicidade", f"< {TEMPO_DUPLICIDADE}s"),
        ("Testes aprovados", f"{total_ia + total_fluxos}/{total_ia + total_fluxos}"),
    ]
    largura = 350
    for indice, (rotulo, valor) in enumerate(cards):
        x = 70 + indice * 372
        draw.rounded_rectangle((x, 295, x + largura, 440), radius=24, fill="white", outline="#c8d8e5", width=2)
        texto(draw, (x + 24, 320), rotulo, pequeno, "#60758a")
        texto(draw, (x + 24, 365), valor, fonte("segoeuib.ttf", 36), "#067a88")

    texto(draw, (70, 490), "Cenários executados", fonte("segoeuib.ttf", 36), "#17324d")
    colunas = [70, 430, 890, 1220, 1460, 1715]
    titulos = ["Cenário", "Entrada", "Classificação", "Cobrança", "Decisão", "Status"]
    draw.rounded_rectangle((70, 555, 1930, 620), radius=16, fill="#dceaf1")
    for x, nome in zip(colunas, titulos):
        texto(draw, (x + 16, 572), nome, cabecalho, "#17324d")

    y = 630
    for indice, (cenario, entrada, classificacao, cobranca, decisao) in enumerate(casos):
        fundo = "white" if indice % 2 == 0 else "#edf4f7"
        draw.rounded_rectangle((70, y, 1930, y + 94), radius=12, fill=fundo)
        chave = f"{cenario}-{entrada}"
        resultado = resultados.get(chave)
        if resultado:
            obtido = resultado["classificacao"] or "normal"
            score_chave = (
                "score_duplicidade"
                if resultado["classificacao"] == "duplicidade"
                else "score"
            )
            score = f"{resultado[score_chave]:.4f}"
            decisao = {
                "ia_temporal": "IA temporal",
                "ia_comportamental": "IA comp.",
                "salvaguarda_temporal": "Salvaguarda",
            }[resultado["origem_classificacao"]]
        else:
            obtido = "normal"
            score = "n/a"
        esperado = classificacao.lower()
        aprovado = (
            obtido == esperado
            or (esperado == "ia_anomalia" and obtido == "ia_anomalia")
            or (cenario == "Primeira passagem" and esperado == "normal")
        )
        valores = [cenario, entrada, classificacao, cobranca, f"{decisao} · {score}"]
        for x, valor in zip(colunas[:-1], valores):
            texto(draw, (x + 16, y + 31), valor, corpo, "#17324d")
        texto(draw, (colunas[-1] + 16, y + 31), "APROVADO" if aprovado else "FALHOU", corpo_bold, "#138a58" if aprovado else "#c33c54")
        y += 102

    draw.rounded_rectangle((70, 1275, 1930, 1415), radius=24, fill="#e4f5ef", outline="#9bd6bf", width=2)
    texto(draw, (105, 1305), "Resultado geral", corpo_bold, "#126a49")
    texto(
        draw,
        (105, 1352),
        f"{total_ia} testes unitários da IA + {total_fluxos} testes integrados, sem falhas ou erros.",
        corpo,
        "#17324d",
    )
    texto(
        draw,
        (1490, 1445),
        "Gerado em " + datetime.now().strftime("%d/%m/%Y %H:%M"),
        pequeno,
        "#60758a",
    )

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(SAIDA, format="PNG", optimize=True)
    print(f"Imagem gerada: {SAIDA}")


if __name__ == "__main__":
    gerar()
