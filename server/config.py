"""Configuración del servidor del tutor.

Todo se puede pisar por variable de entorno; los valores por defecto sirven para
correr local con `uvicorn server.app:app`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Modelo y parámetros de la llamada a Claude.
MODELO = "claude-opus-5-5"
# Conversación breve, una idea por turno: esfuerzo bajo alcanza y responde rápido.
ESFUERZO = "low"
MAX_TOKENS = 4000
# Si el clasificador de seguridad declina un pedido, la API lo reintenta en el
# modelo de respaldo recomendado dentro de la misma llamada.
BETAS = ["server-side-fallback-2026-07-01"]
FALLBACKS = "default"

# Cuántos mensajes previos se mandan como contexto (los más recientes).
MAX_MENSAJES_CONTEXTO = 60
# Largo máximo de un mensaje del estudiante.
MAX_LARGO_MENSAJE = 2000

# Sesiones del estudiante.
DURACION_SESION_HORAS = 24 * 7

# Estudiantes del curso: EST-01 … EST-35.
N_ESTUDIANTES = 35


@dataclass
class Ajustes:
    datos: Path = field(default_factory=lambda: Path(os.environ.get("TUTOR_DATOS", RAIZ / "datos")))
    system_prompt: Path = field(
        default_factory=lambda: Path(os.environ.get("TUTOR_SYSTEM_PROMPT", RAIZ / "tutor" / "system_prompt.md"))
    )
    placeholder: Path = RAIZ / "server" / "system_prompt_placeholder.md"
    web: Path = RAIZ / "web"
    modelo: str = field(default_factory=lambda: os.environ.get("TUTOR_MODELO", MODELO))
    esfuerzo: str = field(default_factory=lambda: os.environ.get("TUTOR_ESFUERZO", ESFUERZO))
    max_tokens: int = MAX_TOKENS
    # Si está definido, los códigos de acceso se derivan de este secreto y el
    # server siembra la tabla de estudiantes al arrancar (ver generar_codigos.py).
    codigos_secreto: str | None = field(default_factory=lambda: os.environ.get("CODIGOS_SECRETO") or None)
    n_estudiantes: int = field(default_factory=lambda: int(os.environ.get("TUTOR_N_ESTUDIANTES", N_ESTUDIANTES)))

    @property
    def db(self) -> Path:
        return self.datos / "tutor.db"
