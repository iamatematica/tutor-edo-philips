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
MODELO = "claude-sonnet-5-5"
# Conversación breve, una idea por turno: con esfuerzo bajo el modelo casi no
# piensa en los pedidos simples y responde rápido.
ESFUERZO = "low"
MAX_TOKENS = 4000
# Si el clasificador de seguridad declina un pedido, la API lo reintenta en el
# modelo de respaldo recomendado dentro de la misma llamada.
BETAS = ["server-side-fallback-2026-07-01"]
FALLBACKS = "default"

# Memoria acotada: a la API van solo los últimos 12 turnos de la sesión
# (turno = mensaje del estudiante + respuesta del tutor).
MAX_TURNOS_CONTEXTO = 12
# Largo máximo de un mensaje del estudiante.
MAX_LARGO_MENSAJE = 2000

# Una sesión se da por cerrada tras estos minutos sin mensajes.
MINUTOS_SESION = 20
# Cuánto vale el ingreso en el teléfono antes de pedir el código otra vez.
DURACION_TOKEN_HORAS = 24 * 7

# Límite diario de turnos por alumno; se reinicia a las 0:00 de Buenos Aires.
LIMITE_TURNOS_DIA = 80
ZONA_HORARIA = "America/Argentina/Buenos_Aires"

# Costo medio por turno, para el indicador de costo del panel docente.
# Estimación inicial: 200 US$ / (35 alumnos x 3 sesiones x 80 turnos x 4 semanas)
# ≈ 0,006 US$. Recalibrar con el gasto real que muestra la consola de la API.
COSTO_MEDIO_TURNO_USD = 0.006
# Tope mensual que el docente fija en la consola de la API (no lo aplica el server).
TOPE_MENSUAL_USD = 200

# Estudiantes del curso: EST-01 … EST-35.
N_ESTUDIANTES = 35

# Modo demostración (TUTOR_DEMO=1): tutor guionado sin API ni costo, base sembrada
# con datos inventados y clave del panel "demo" si no se define DOCENTE_KEY.
DOCENTE_KEY_DEMO = "demo"


def _demo_activo() -> bool:
    return os.environ.get("TUTOR_DEMO", "").strip().lower() in {"1", "true", "si", "sí"}


@dataclass
class Ajustes:
    datos: Path = field(default_factory=lambda: Path(os.environ.get("TUTOR_DATOS", RAIZ / "datos")))
    system_prompt: Path = field(
        default_factory=lambda: Path(os.environ.get("TUTOR_SYSTEM_PROMPT", RAIZ / "tutor" / "system_prompt.md"))
    )
    placeholder: Path = RAIZ / "server" / "system_prompt_placeholder.md"
    banco: Path = RAIZ / "tutor" / "banco"
    demo: bool = field(default_factory=_demo_activo)
    web: Path = RAIZ / "web"
    panel: Path = RAIZ / "panel"
    modelo: str = field(default_factory=lambda: os.environ.get("TUTOR_MODELO", MODELO))
    esfuerzo: str = field(default_factory=lambda: os.environ.get("TUTOR_ESFUERZO", ESFUERZO))
    max_tokens: int = MAX_TOKENS
    # Si está definido, los códigos de acceso se derivan de este secreto y el
    # server siembra la tabla de estudiantes al arrancar (ver generar_codigos.py).
    codigos_secreto: str | None = field(default_factory=lambda: os.environ.get("CODIGOS_SECRETO") or None)
    n_estudiantes: int = field(default_factory=lambda: int(os.environ.get("TUTOR_N_ESTUDIANTES", N_ESTUDIANTES)))
    limite_turnos_dia: int = field(
        default_factory=lambda: int(os.environ.get("TUTOR_LIMITE_TURNOS_DIA", LIMITE_TURNOS_DIA))
    )
    # Firma de los tokens de ingreso. Si no se define, se genera uno y se guarda en datos/.
    sesion_secreto: str | None = field(default_factory=lambda: os.environ.get("SESION_SECRETO") or None)
    # Clave del panel docente. Sin ella, /api/metricas responde 503.
    docente_key: str | None = field(default_factory=lambda: os.environ.get("DOCENTE_KEY") or None)
    costo_medio_turno: float = field(
        default_factory=lambda: float(os.environ.get("TUTOR_COSTO_MEDIO_TURNO", COSTO_MEDIO_TURNO_USD))
    )
    tope_mensual: float = TOPE_MENSUAL_USD

    def __post_init__(self):
        if self.demo and not self.docente_key:
            self.docente_key = DOCENTE_KEY_DEMO

    @property
    def db(self) -> Path:
        return self.datos / "tutor.db"
