# regra de anomalia
from sqlalchemy.orm import Session
from app.models import EventoPassagem
from datetime import datetime
from app.config import TEMPO_DUPLICIDADE


# analisa eventos novos
def analisar_eventos(db: Session):
    eventos = (
        db.query(EventoPassagem)
        .filter(EventoPassagem.processado == 0)
        .order_by(EventoPassagem.id.asc())
        .all()
    )

    ultimo_evento_por_chave = {}

    for evento in eventos:
        chave = (evento.id_veiculo, evento.faixa)

        try:
            tempo_atual = datetime.fromisoformat(evento.timestamp_evento)
        except ValueError:
            evento.anomalia = "duplicidade"
            evento.processado = 1
            continue

        if chave in ultimo_evento_por_chave:
            tempo_anterior = ultimo_evento_por_chave[chave]
            diferenca = (tempo_atual - tempo_anterior).total_seconds()

            if diferenca < TEMPO_DUPLICIDADE:
                evento.anomalia = "duplicidade"

        ultimo_evento_por_chave[chave] = tempo_atual
        evento.processado = 1

    db.commit()
