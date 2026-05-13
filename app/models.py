from sqlalchemy import Column, Integer, String, Float
from app.database import Base

# tabela principal
class EventoPassagem(Base):
    __tablename__ = "eventos_passagem"

    id = Column(Integer, primary_key=True, index=True)  
    id_veiculo = Column(String, nullable=False)          
    faixa = Column(Integer, nullable=False)              
    timestamp_evento = Column(String, nullable=False)    
    sensor_id = Column(String, nullable=True)            
    origem = Column(String, nullable=True)               
    valor = Column(Float, default=5.0)                   
    processado = Column(Integer, default=0)              
    anomalia = Column(String, nullable=True)             

