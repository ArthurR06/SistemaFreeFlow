# operações banco
from sqlalchemy.orm import Session
from datetime import datetime

from app import models, schemas
from app.config import valor_passagem_por_faixa
from app.security import gerar_hash_senha, verificar_senha


# ==========================================================
# USUÁRIOS DAS CONCESSIONÁRIAS
# ==========================================================

def buscar_usuario_concessionaria(
    db: Session,
    usuario: str
):
    if not usuario:
        return None

    return (
        db.query(models.UsuarioConcessionaria)
        .filter(
            models.UsuarioConcessionaria.usuario
            == usuario.strip()
        )
        .first()
    )


def autenticar_usuario_concessionaria(
    db: Session,
    usuario: str,
    senha: str
):
    usuario_db = buscar_usuario_concessionaria(
        db,
        usuario
    )

    if (
        not usuario_db
        or usuario_db.ativo != 1
        or not senha
        or not verificar_senha(
            senha,
            usuario_db.senha_hash
        )
    ):
        return None

    return usuario_db


def obter_faixas_usuario_concessionaria(
    usuario: models.UsuarioConcessionaria
):
    faixas = []

    for faixa in usuario.faixas_permitidas.split(","):
        try:
            faixas.append(int(faixa.strip()))
        except ValueError:
            continue

    return faixas


def inicializar_usuarios_concessionarias(
    db: Session,
    credenciais: dict
):
    """Cadastra os usuários demonstrativos que ainda não existem."""
    usuarios_criados = 0

    for nome_usuario, dados in credenciais.items():
        existente = buscar_usuario_concessionaria(
            db,
            nome_usuario
        )

        if existente:
            continue

        usuario_db = models.UsuarioConcessionaria(
            usuario=nome_usuario.strip(),
            senha_hash=gerar_hash_senha(
                dados["senha"]
            ),
            concessionaria_id=dados["id"],
            concessionaria_nome=dados["nome"],
            faixas_permitidas=",".join(
                str(faixa)
                for faixa in dados["faixas"]
            ),
            ativo=1,
            criado_em=datetime.now().isoformat(
                timespec="seconds"
            )
        )

        db.add(usuario_db)
        usuarios_criados += 1

    if usuarios_criados:
        db.commit()

    return usuarios_criados


# ==========================================================
# EVENTOS
# ==========================================================

# cria evento
def criar_evento(db: Session, evento: schemas.EventoCreate):
    db_evento = models.EventoPassagem(
        id_veiculo=evento.id_veiculo,
        faixa=evento.faixa,
        timestamp_evento=evento.timestamp_evento,
        sensor_id=evento.sensor_id,
        origem=evento.origem,
        valor=valor_passagem_por_faixa(evento.faixa)
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
        .filter(
            models.EventoPassagem.anomalia == "duplicidade"
        )
        .count()
    )


# soma total
def total_gerado(db: Session):
    eventos = db.query(models.EventoPassagem).all()

    return sum(
        e.valor
        for e in eventos
        if e.anomalia is None
    )


# últimas duplicidades
def ultimas_duplicidades(db: Session, limite: int = 5):
    return (
        db.query(models.EventoPassagem)
        .filter(
            models.EventoPassagem.anomalia == "duplicidade"
        )
        .order_by(models.EventoPassagem.id.desc())
        .limit(limite)
        .all()
    )


# ==========================================================
# PROPRIETÁRIOS
# ==========================================================

def criar_proprietario(
    db: Session,
    proprietario: schemas.ProprietarioCreate
):
    db_proprietario = models.Proprietario(
        nome=proprietario.nome.strip(),
        cpf=proprietario.cpf.strip()
    )

    db.add(db_proprietario)
    db.commit()
    db.refresh(db_proprietario)

    return db_proprietario


def listar_proprietarios(db: Session):
    return (
        db.query(models.Proprietario)
        .order_by(models.Proprietario.nome.asc())
        .all()
    )


def buscar_proprietario_por_id(
    db: Session,
    proprietario_id: int
):
    return (
        db.query(models.Proprietario)
        .filter(
            models.Proprietario.id == proprietario_id
        )
        .first()
    )


def buscar_proprietario_por_cpf(
    db: Session,
    cpf: str
):
    return (
        db.query(models.Proprietario)
        .filter(
            models.Proprietario.cpf == cpf
        )
        .first()
    )


# ==========================================================
# VEÍCULOS
# ==========================================================

def criar_veiculo(
    db: Session,
    veiculo: schemas.VeiculoCreate
):
    uid = None

    if veiculo.uid_rfid:
        uid = veiculo.uid_rfid.strip().upper()

    db_veiculo = models.Veiculo(
        placa=veiculo.placa.strip().upper(),
        uid_rfid=uid,
        proprietario_id=veiculo.proprietario_id
    )

    db.add(db_veiculo)
    db.commit()
    db.refresh(db_veiculo)

    return db_veiculo


def listar_veiculos(db: Session):
    return (
        db.query(models.Veiculo)
        .order_by(models.Veiculo.placa.asc())
        .all()
    )


def buscar_veiculo_por_id(
    db: Session,
    veiculo_id: int
):
    return (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.id == veiculo_id
        )
        .first()
    )


def buscar_veiculo_por_placa(
    db: Session,
    placa: str
):
    return (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.placa == placa.strip().upper()
        )
        .first()
    )


def buscar_veiculo_por_uid(
    db: Session,
    uid_rfid: str
):
    return (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.uid_rfid
            == uid_rfid.strip().upper()
        )
        .first()
    )


# ==========================================================
# ASSOCIAR RFID AO VEÍCULO
# ==========================================================

def associar_rfid(
    db: Session,
    veiculo_id: int,
    uid_rfid: str
):
    veiculo = buscar_veiculo_por_id(
        db,
        veiculo_id
    )

    if not veiculo:
        return None

    veiculo.uid_rfid = (
        uid_rfid
        .strip()
        .upper()
    )

    db.commit()
    db.refresh(veiculo)

    return veiculo


# ==========================================================
# COBRANÇAS
# ==========================================================

def criar_cobranca(
    db: Session,
    evento: models.EventoPassagem,
    veiculo: models.Veiculo
):
    # Não permite cobrança duplicada
    existente = (
        db.query(models.Cobranca)
        .filter(
            models.Cobranca.evento_id == evento.id
        )
        .first()
    )

    if existente:
        return existente

    db_cobranca = models.Cobranca(
        evento_id=evento.id,
        veiculo_id=veiculo.id,
        valor=evento.valor,
        status="pendente",
        timestamp_criacao=datetime.now().isoformat(
            timespec="seconds"
        )
    )

    db.add(db_cobranca)
    db.commit()
    db.refresh(db_cobranca)

    return db_cobranca


def listar_cobrancas(db: Session):
    return (
        db.query(models.Cobranca)
        .order_by(models.Cobranca.id.desc())
        .all()
    )


def contar_cobrancas(db: Session):
    return db.query(
        models.Cobranca
    ).count()


def contar_cobrancas_pendentes(db: Session):
    return (
        db.query(models.Cobranca)
        .filter(
            models.Cobranca.status == "pendente"
        )
        .count()
    )


def contar_cobrancas_pagas(db: Session):
    return (
        db.query(models.Cobranca)
        .filter(
            models.Cobranca.status == "pago"
        )
        .count()
    )


def valor_total_cobrancas(db: Session):
    cobrancas = db.query(
        models.Cobranca
    ).all()

    return sum(
        cobranca.valor
        for cobranca in cobrancas
    )
