"""Valida, pela credencial real da aplicacao, os limites do papel Postgres."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
TABLES = (
    "proprietarios",
    "veiculos",
    "eventos_passagem",
    "cobrancas",
    "usuarios_concessionarias",
)


def connect():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10)


def expect_denied(label: str, sql: str) -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except psycopg2.Error as error:
                connection.rollback()
                if error.pgcode != "42501":
                    raise AssertionError(
                        f"{label}: SQLSTATE inesperado {error.pgcode!r}"
                    ) from error
                print(f"PASS  {label}: negado (SQLSTATE 42501)")
                return

            connection.rollback()
            raise AssertionError(f"{label}: a operacao proibida foi aceita")
    finally:
        connection.close()


def assert_metadata() -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select current_user, rolsuper, rolcreatedb, rolcreaterole,
                       rolbypassrls, rolcanlogin
                from pg_roles
                where rolname = current_user
                """
            )
            role = cursor.fetchone()
            assert role == ("freeflow_app", False, False, False, False, True), role

            cursor.execute(
                "select has_schema_privilege(current_user, 'public', 'CREATE')"
            )
            assert cursor.fetchone() == (False,)

            cursor.execute(
                """
                select c.relname, c.relrowsecurity, r.rolname = current_user as owner
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                join pg_roles r on r.oid = c.relowner
                where n.nspname = 'public' and c.relname = any(%s)
                order by c.relname
                """,
                (list(TABLES),),
            )
            table_security = cursor.fetchall()
            assert len(table_security) == len(TABLES), table_security
            assert all(rls_enabled and not is_owner for _, rls_enabled, is_owner in table_security)

            for table in TABLES:
                cursor.execute(
                    "select has_table_privilege(current_user, %s, 'DELETE')",
                    (f"public.{table}",),
                )
                assert cursor.fetchone() == (False,), table

        print("PASS  atributos: sem SUPERUSER, CREATEDB, CREATEROLE ou BYPASSRLS")
        print("PASS  ownership: nao e dono das tabelas e todas estao com RLS")
        print("PASS  grants: sem CREATE no schema e sem DELETE nas cinco tabelas")
    finally:
        connection.rollback()
        connection.close()


def assert_allowed_write_rolls_back() -> None:
    connection = connect()
    marker = f"TESTE-{uuid.uuid4()}"
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.proprietarios (nome, cpf)
                values (%s, %s)
                returning id
                """,
                ("Teste temporario de permissoes", marker),
            )
            row_id = cursor.fetchone()[0]
            cursor.execute(
                "update public.proprietarios set nome = %s where id = %s returning id",
                ("Teste temporario atualizado", row_id),
            )
            assert cursor.fetchone() == (row_id,)
        connection.rollback()
        print("PASS  operacao permitida: INSERT e UPDATE funcionam (rollback aplicado)")
    finally:
        connection.rollback()
        connection.close()


def main() -> int:
    load_dotenv(ROOT_DIR / ".env.local", override=False)
    if not os.environ.get("DATABASE_URL"):
        print("ERRO  DATABASE_URL nao configurada", file=sys.stderr)
        return 2

    try:
        assert_metadata()
        assert_allowed_write_rolls_back()

        for table in TABLES:
            expect_denied(
                f"DELETE public.{table}",
                f"delete from public.{table} where false",
            )
            expect_denied(
                f"DROP public.{table}",
                f"drop table public.{table}",
            )
            expect_denied(
                f"ALTER public.{table}",
                f"alter table public.{table} add column teste_permissao boolean",
            )
            expect_denied(
                f"RLS off public.{table}",
                f"set local row_security = off; select count(*) from public.{table}",
            )

        expect_denied("SET ROLE postgres", "set role postgres")
        expect_denied(
            "ALTER ROLE BYPASSRLS",
            "alter role freeflow_app bypassrls",
        )
    except (AssertionError, KeyError, psycopg2.Error) as error:
        print(f"FALHA {error}", file=sys.stderr)
        return 1

    print("RESULTADO: todos os limites de seguranca foram confirmados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
