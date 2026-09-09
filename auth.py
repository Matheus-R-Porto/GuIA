"""Hash e verificação de senha para os perfis locais do GuIA.

Uso local: perfis compartilhando um PC (aluno/professor), não autenticação
de rede. PBKDF2 da stdlib é suficiente aqui e evita adicionar dependência
nova (bcrypt/passlib) só para isso.
"""
import hashlib
import hmac
import os

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Gera "salt$hash" em hex. Nunca guarde a senha em texto puro."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Confere a senha contra o hash salvo. Retorna False se o hash estiver
    vazio/malformado — quem chama decide separadamente se um perfil sem
    senha (legado) deve pular essa checagem."""
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    # compare_digest em vez de == : comparação de string comum vaza timing
    # (retorna assim que o primeiro caractere diverge), o que em teoria
    # permite adivinhar o hash por medição de tempo. Custa nada trocar.
    return hmac.compare_digest(digest.hex(), digest_hex)
