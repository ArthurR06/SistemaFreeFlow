# conexão banco
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# ajuste pro sqlite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# engine
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base modelos
Base = declarative_base()


# abre/fecha sessão
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
