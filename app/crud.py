# operações banco
from sqlalchemy.orm import Session
from app import models, schemas
from app.config import VALOR_PASSAGEM


# cria evento
def criar_evento(db: Session, evento: schemas.EventoCreate):
    db_evento = models.EventoPassagem(
        id_veiculo=evento.id_veiculo,
        faixa=evento.faixa,
        timestamp_evento=evento.timestamp_evento,
        sensor_id=evento.sensor_id,
        origem=evento.origem,
        valor=VALOR_PASSAGEM
    )
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento


# últimos eventos
def listar_eventos(db: Session, limite: int = 20):
    return (
        db.query(models.EventoPassagem)
        .order_by(models.EventoPassagem.id.desc())
        .limit(limite)
        .all()
    )


# todos eventos
def listar_todos_eventos(db: Session):
    return (
        db.query(models.EventoPassagem)
        .order_by(models.EventoPassagem.id.desc())
        .all()
    )


# contagem
def contar_eventos(db: Session):
    return db.query(models.EventoPassagem).count()


# conta duplicidade
def contar_duplicidades(db: Session):
    return (
        db.query(models.EventoPassagem)
        .filter(models.EventoPassagem.anomalia == "duplicidade")
        .count()
    )


# soma total
def total_gerado(db: Session):
    eventos = db.query(models.EventoPassagem).all()
    return sum(e.valor for e in eventos)


# últimas duplicidades
def ultimas_duplicidades(db: Session, limite: int = 5):
    return (
        db.query(models.EventoPassagem)
        .filter(models.EventoPassagem.anomalia == "duplicidade")
        .order_by(models.EventoPassagem.id.desc())
        .limit(limite)
        .all()
    )
