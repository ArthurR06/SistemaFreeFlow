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
