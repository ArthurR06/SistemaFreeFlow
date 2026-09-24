# conexão banco
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.config import DATABASE_URL

# SQLite permanece disponível somente como alternativa de desenvolvimento.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Vercel cria instâncias sob demanda. O Supabase já fornece o pool de
    # transações, então cada execução deve devolver a conexão imediatamente.
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",
        },
    )

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
