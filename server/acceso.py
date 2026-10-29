"""Identificadores seudonimizados, códigos de acceso y tokens de sesión.

No se guarda ningún dato personal: solo EST-NN y el hash del código.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

# Sin 0/O, 1/I/L ni 5/S: se dictan y se copian del papel sin confusiones.
ALFABETO = "ABCDEFGHJKMNPQRTUVWXYZ2346789"
LARGO_CODIGO = 6
ITERACIONES = 200_000


def id_estudiante(n: int) -> str:
    return f"EST-{n:02d}"


def normalizar_id(texto: str) -> str | None:
    """Acepta 'EST-07', 'est07', 'EST 7' o '7' y devuelve 'EST-07'."""
    m = re.fullmatch(r"\s*(?:EST)?[\s\-_]*(\d{1,2})\s*", texto or "", re.IGNORECASE)
    if not m:
        return None
    n = int(m.group(1))
    return id_estudiante(n) if n >= 1 else None


def normalizar_codigo(texto: str) -> str:
    return re.sub(r"[\s\-]", "", texto or "").upper()


def codigo_aleatorio() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))


def codigo_derivado(secreto: str, est_id: str) -> str:
    """Código reproducible a partir de un secreto del docente (HMAC-SHA256)."""
    digest = hmac.new(secreto.encode(), est_id.encode(), hashlib.sha256).digest()
    n = int.from_bytes(digest, "big")
    letras = []
    for _ in range(LARGO_CODIGO):
        n, r = divmod(n, len(ALFABETO))
        letras.append(ALFABETO[r])
    return "".join(letras)


def formatear_codigo(codigo: str) -> str:
    """'ABC234' → 'ABC-234', para imprimir."""
    return f"{codigo[:3]}-{codigo[3:]}"


def hash_codigo(codigo: str, sal: str | None = None) -> str:
    sal = sal or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", normalizar_codigo(codigo).encode(), bytes.fromhex(sal), ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal}${h.hex()}"


def verificar_codigo(codigo: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = guardado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    h = hashlib.pbkdf2_hmac("sha256", normalizar_codigo(codigo).encode(), bytes.fromhex(sal), int(iteraciones))
    return hmac.compare_digest(h.hex(), esperado)


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
