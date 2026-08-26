from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


# ==========================================================
# PROPRIETÁRIOS
# ==========================================================

class Proprietario(Base):
    __tablename__ = "proprietarios"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    nome = Column(
        String,
        nullable=False
    )

    cpf = Column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    # Um proprietário pode possuir vários veículos
    veiculos = relationship(
        "Veiculo",
        back_populates="proprietario"
    )


# ==========================================================
# VEÍCULOS
# ==========================================================

class Veiculo(Base):
    __tablename__ = "veiculos"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    placa = Column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    # Pode ficar vazio enquanto a tag ainda não foi associada
    uid_rfid = Column(
        String,
        nullable=True,
        unique=True,
        index=True
    )

    proprietario_id = Column(
        Integer,
        ForeignKey("proprietarios.id"),
        nullable=False
    )

    proprietario = relationship(
        "Proprietario",
        back_populates="veiculos"
    )

    cobrancas = relationship(
        "Cobranca",
        back_populates="veiculo"
    )


# ==========================================================
# EVENTOS DE PASSAGEM
# ==========================================================

class EventoPassagem(Base):
    __tablename__ = "eventos_passagem"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    id_veiculo = Column(
        String,
        nullable=False
    )

    faixa = Column(
        Integer,
        nullable=False
    )

    timestamp_evento = Column(
        String,
        nullable=False
    )

    sensor_id = Column(
        String,
        nullable=True
    )

    origem = Column(
        String,
        nullable=True
    )

    valor = Column(
        Float,
        default=5.0
    )

    processado = Column(
        Integer,
        default=0
    )

    anomalia = Column(
        String,
        nullable=True
    )


# ==========================================================
# COBRANÇAS
# ==========================================================

class Cobranca(Base):
    __tablename__ = "cobrancas"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Cada evento pode gerar no máximo uma cobrança
    evento_id = Column(
        Integer,
        ForeignKey("eventos_passagem.id"),
        nullable=False,
        unique=True
    )

    veiculo_id = Column(
        Integer,
        ForeignKey("veiculos.id"),
        nullable=False
    )

    valor = Column(
        Float,
        nullable=False,
        default=5.0
    )

    status = Column(
        String,
        nullable=False,
        default="pendente"
    )

    timestamp_criacao = Column(
        String,
        nullable=False
    )

    veiculo = relationship(
        "Veiculo",
        back_populates="cobrancas"
    )

    evento = relationship(
        "EventoPassagem"
    )