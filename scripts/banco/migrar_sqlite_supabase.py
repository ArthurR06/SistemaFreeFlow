"""Copia os dados do SQLite local para o PostgreSQL configurado no ambiente."""

import argparse
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool

from app.config import BASE_DIR, DATABASE_URL


TABELAS = (
    "proprietarios",
    "veiculos",
    "eventos_passagem",
    "cobrancas",
    "usuarios_concessionarias",
)


def url_sqlite(caminho: Path) -> str:
    return "sqlite:///" + caminho.resolve().as_posix()


def migrar(caminho_sqlite: Path) -> dict[str, int]:
    if DATABASE_URL.startswith("sqlite"):
        raise RuntimeError(
            "DATABASE_URL deve apontar para o Supabase antes da importação."
        )
    if not caminho_sqlite.exists():
        raise FileNotFoundError(caminho_sqlite)

    origem = create_engine(
        url_sqlite(caminho_sqlite),
        connect_args={"check_same_thread": False},
    )
    destino = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"sslmode": "require", "connect_timeout": 10},
    )

    meta_origem = MetaData()
    meta_destino = MetaData()
    meta_origem.reflect(bind=origem, only=TABELAS)
    meta_destino.reflect(bind=destino, only=TABELAS)
    totais: dict[str, int] = {}

    with origem.connect() as conexao_origem, destino.begin() as conexao_destino:
        for nome in TABELAS:
            tabela_origem: Table = meta_origem.tables[nome]
            tabela_destino: Table = meta_destino.tables[nome]
            registros = [
                dict(linha._mapping)
                for linha in conexao_origem.execute(select(tabela_origem))
            ]

            if registros:
                comando = insert(tabela_destino).values(registros)
                atualizaveis = {
                    coluna.name: comando.excluded[coluna.name]
                    for coluna in tabela_destino.columns
                    if not coluna.primary_key
                }
                conexao_destino.execute(
                    comando.on_conflict_do_update(
                        index_elements=[tabela_destino.c.id],
                        set_=atualizaveis,
                    )
                )

            totais[nome] = len(registros)

        for nome in TABELAS:
            tabela = meta_destino.tables[nome]
            maior_id = conexao_destino.scalar(select(func.max(tabela.c.id))) or 0
            sequencia = conexao_destino.scalar(
                select(func.pg_get_serial_sequence(f"public.{nome}", "id"))
            )
            if sequencia:
                conexao_destino.exec_driver_sql(
                    "select setval(%s, %s, %s)",
                    (sequencia, max(maior_id, 1), maior_id > 0),
                )

    origem.dispose()
    destino.dispose()
    return totais


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=BASE_DIR / "data" / "freeflow.db",
    )
    argumentos = parser.parse_args()
    totais = migrar(argumentos.sqlite)

    for tabela, total in totais.items():
        print(f"{tabela}: {total} registro(s)")


if __name__ == "__main__":
    main()
