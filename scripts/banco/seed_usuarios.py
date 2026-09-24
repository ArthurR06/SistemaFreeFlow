"""Cria os acessos demonstrativos depois que as migrations forem aplicadas."""

from app.config import CONCESSIONARIAS_ADMIN
from app.crud import inicializar_usuarios_concessionarias
from app.database import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        criados = inicializar_usuarios_concessionarias(
            db,
            CONCESSIONARIAS_ADMIN,
        )

    print(f"Usuários criados: {criados}")


if __name__ == "__main__":
    main()
