import hashlib
import hmac
import secrets


ALGORITMO = "pbkdf2_sha256"
ITERACOES = 600_000


def gerar_hash_senha(senha: str) -> str:
    """Gera um hash PBKDF2 com salt aleatório para armazenamento no banco."""
    salt = secrets.token_bytes(16)
    hash_senha = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        ITERACOES,
    )

    return (
        f"{ALGORITMO}${ITERACOES}$"
        f"{salt.hex()}${hash_senha.hex()}"
    )


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Compara uma senha com o hash salvo sem expor o valor original."""
    try:
        algoritmo, iteracoes, salt_hex, hash_esperado = senha_hash.split("$")

        if algoritmo != ALGORITMO:
            return False

        hash_informado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iteracoes),
        ).hex()

    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(hash_informado, hash_esperado)
