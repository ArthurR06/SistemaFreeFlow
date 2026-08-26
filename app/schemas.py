# valida dados da api
from pydantic import BaseModel


# entrada
class EventoCreate(BaseModel):
    id_veiculo: str
    faixa: int
    timestamp_evento: str
    sensor_id: str | None = None
    origem: str | None = None


# saída
class EventoResponse(BaseModel):
    id: int
    id_veiculo: str
    faixa: int
    timestamp_evento: str
    sensor_id: str | None = None
    origem: str | None = None
    valor: float
    processado: int
    anomalia: str | None = None

    class Config:
        from_attributes = True

# =========================
# PROPRIETÁRIOS
# =========================

class ProprietarioCreate(BaseModel):
    nome: str
    cpf: str


class ProprietarioResponse(BaseModel):
    id: int
    nome: str
    cpf: str

    class Config:
        from_attributes = True


# =========================
# VEÍCULOS
# =========================

class VeiculoCreate(BaseModel):
    placa: str
    proprietario_id: int
    uid_rfid: str | None = None


class VeiculoResponse(BaseModel):
    id: int
    placa: str
    uid_rfid: str | None = None
    proprietario_id: int

    class Config:
        from_attributes = True


# =========================
# ASSOCIAÇÃO DE RFID
# =========================

class AssociarRFID(BaseModel):
    uid_rfid: str


# =========================
# COBRANÇAS
# =========================

class CobrancaResponse(BaseModel):
    id: int
    evento_id: int
    veiculo_id: int
    valor: float
    status: str
    timestamp_criacao: str

    class Config:
        from_attributes = True

        # =========================
# PORTAL DO CLIENTE
# =========================

class PortalConsulta(BaseModel):
    cpf: str
    placa: str


class PortalPagamento(BaseModel):
    cpf: str
    placa: str