"""Gera SQL idempotente para importar o SQLite pelo Supabase CLI."""

import argparse
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


TABELAS = (
    "proprietarios",
    "veiculos",
    "eventos_passagem",
    "cobrancas",
    "usuarios_concessionarias",
)


def literal_sql(valor: object) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, (int, float)):
        return str(valor)
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"


def gerar(caminho_sqlite: Path) -> str:
    if not caminho_sqlite.exists():
        raise FileNotFoundError(caminho_sqlite)

    blocos = ["begin;"]

    with sqlite3.connect(caminho_sqlite) as conexao:
        conexao.row_factory = sqlite3.Row

        for tabela in TABELAS:
            registros = conexao.execute(
                f'select * from "{tabela}" order by id'
            ).fetchall()

            for registro in registros:
                colunas = tuple(registro.keys())
                nomes = ", ".join(f'"{coluna}"' for coluna in colunas)
                valores = ", ".join(
                    literal_sql(registro[coluna]) for coluna in colunas
                )
                atualizacoes = ", ".join(
                    f'"{coluna}" = excluded."{coluna}"'
                    for coluna in colunas
                    if coluna != "id"
                )
                blocos.append(
                    f'insert into public."{tabela}" ({nomes}) '
                    f"values ({valores}) on conflict (id) do update set "
                    f"{atualizacoes};"
                )

            blocos.append(
                "select setval("
                f"pg_get_serial_sequence('public.{tabela}', 'id'), "
                f"greatest(coalesce((select max(id) from public.\"{tabela}\"), 1), 1), "
                f"exists(select 1 from public.\"{tabela}\"));"
            )

    blocos.append("commit;")
    return "\n".join(blocos) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=BASE_DIR / "data" / "freeflow.db",
    )
    parser.add_argument("--output", type=Path, required=True)
    argumentos = parser.parse_args()
    argumentos.output.write_text(
        gerar(argumentos.sqlite),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
