# api principal
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import schemas, crud, anomaly
from app.config import (
    VALOR_PASSAGEM,
    TEMPO_SEM_DADOS_ALERTA,
    REFRESH_SEGUNDOS
)

import csv
import io
from datetime import datetime

# cria tabelas
Base.metadata.create_all(bind=engine)

# app
app = FastAPI(title="Free Flow Dashboard AWS Ready")

# templates
templates = Jinja2Templates(directory="app/templates")


# formata tempo em segundos, minutos ou horas
def formatar_tempo(segundos: int) -> str:
    if segundos < 60:
        return f"{segundos} segundo(s)"
    elif segundos < 3600:
        minutos = segundos // 60
        return f"{minutos} minuto(s)"
    else:
        horas = segundos // 3600
        return f"{horas} hora(s)"


# teste
@app.get("/")
def raiz():
    return {"mensagem": "API Free Flow funcionando"}


# cria evento
@app.post("/evento", response_model=schemas.EventoResponse)
def criar_evento(evento: schemas.EventoCreate, db: Session = Depends(get_db)):
    return crud.criar_evento(db, evento)


# roda análise
@app.post("/analisar")
def analisar(db: Session = Depends(get_db)):
    anomaly.analisar_eventos(db)
    return {"mensagem": "Análise concluída"}


# lista eventos
@app.get("/eventos", response_model=list[schemas.EventoResponse])
def listar_eventos(db: Session = Depends(get_db)):
    return crud.listar_eventos(db)


# dashboard
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# dados do dashboard
@app.get("/dashboard-data")
def dashboard_data(db: Session = Depends(get_db)):
    eventos = crud.listar_eventos(db, limite=20)
    total_eventos = crud.contar_eventos(db)
    total_duplicidades = crud.contar_duplicidades(db)
    total_gerado = crud.total_gerado(db)
    duplicidades_recentes = crud.ultimas_duplicidades(db, limite=5)

    # última passagem: tenta pegar uma sem anomalia
    ultimo_evento_ok = next((e for e in eventos if e.anomalia is None), None)
    ultimo_evento = ultimo_evento_ok if ultimo_evento_ok else (eventos[0] if eventos else None)

    # monitoramento
    status_operacao = "Recebendo dados normalmente"
    segundos_sem_evento = 0
    nivel_atualizacao = "ok"
    mensagem_atualizacao = "✅ Última atualização há 0 segundo(s)"

    if eventos:
        try:
            horario_ultimo_evento = datetime.fromisoformat(eventos[0].timestamp_evento)
            agora = datetime.now()
            segundos_sem_evento = int((agora - horario_ultimo_evento).total_seconds())
            tempo_formatado = formatar_tempo(segundos_sem_evento)

            if segundos_sem_evento <= 30:
                nivel_atualizacao = "ok"
                mensagem_atualizacao = f"✅ Última atualização há {tempo_formatado}"
                status_operacao = "Recebendo dados normalmente"

            elif segundos_sem_evento <= TEMPO_SEM_DADOS_ALERTA:
                nivel_atualizacao = "atencao"
                mensagem_atualizacao = f"⚠️ Atenção: última atualização há {tempo_formatado}"
                status_operacao = "Atenção: atraso na atualização"

            else:
                nivel_atualizacao = "alerta"
                mensagem_atualizacao = f"🚨 Alerta: última atualização há {tempo_formatado}"
                status_operacao = "Alerta: sem dados recentes"

        except ValueError:
            nivel_atualizacao = "alerta"
            mensagem_atualizacao = "🚨 Alerta: horário inválido no último evento"
            status_operacao = "Alerta: horário inválido no último evento"
    else:
        nivel_atualizacao = "alerta"
        mensagem_atualizacao = "🚨 Alerta: nenhum evento recebido"
        status_operacao = "Alerta: nenhum evento recebido"

    return {
        "total_veiculos": total_eventos,
        "total_gerado": total_gerado,
        "valor_por_passagem": VALOR_PASSAGEM,
        "refresh_segundos": REFRESH_SEGUNDOS,
        "ultima_passagem": {
            "id_veiculo": ultimo_evento.id_veiculo if ultimo_evento else "-",
            "faixa": ultimo_evento.faixa if ultimo_evento else "-",
            "timestamp_evento": ultimo_evento.timestamp_evento if ultimo_evento else "-",
            "valor": ultimo_evento.valor if ultimo_evento else VALOR_PASSAGEM,
            "anomalia": ultimo_evento.anomalia if ultimo_evento else None,
        },
        "eventos": [
            {
                "id_veiculo": e.id_veiculo,
                "faixa": e.faixa,
                "timestamp_evento": e.timestamp_evento,
                "valor": e.valor,
                "anomalia": e.anomalia,
            }
            for e in eventos
        ],
        "total_duplicidades": total_duplicidades,
        "duplicidades_recentes": [
            {
                "id_veiculo": e.id_veiculo,
                "timestamp_evento": e.timestamp_evento
            }
            for e in duplicidades_recentes
        ],
        "status_operacao": status_operacao,
        "segundos_sem_evento": segundos_sem_evento,
        "nivel_atualizacao": nivel_atualizacao,
        "mensagem_atualizacao": mensagem_atualizacao
    }


# exporta csv
@app.get("/exportar-csv")
def exportar_csv(anomalia: str = "todos", db: Session = Depends(get_db)):
    eventos = crud.listar_todos_eventos(db)

    if anomalia == "duplicidade":
        eventos = [e for e in eventos if e.anomalia == "duplicidade"]
    elif anomalia == "ok":
        eventos = [e for e in eventos if e.anomalia is None]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["ID do Veículo", "Faixa", "Data/Hora", "Valor", "Anomalia"])

    for e in eventos:
        writer.writerow([
            e.id_veiculo,
            e.faixa,
            e.timestamp_evento,
            e.valor,
            e.anomalia if e.anomalia else "OK"
        ])

    output.seek(0)
    nome_arquivo = f"relatorio_freeflow_{anomalia}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )
