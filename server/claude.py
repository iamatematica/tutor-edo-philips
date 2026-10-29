"""Llamada a la API de Claude con el SDK oficial `anthropic`.

La clave va en la variable de entorno ANTHROPIC_API_KEY; acá no se escribe nunca.
"""
from __future__ import annotations

import logging
from typing import Protocol

import anthropic

from . import config

log = logging.getLogger("tutor.claude")

# Lo que ve el estudiante si el pedido es declinado por los filtros de seguridad.
TEXTO_DECLINADO = (
    "Eso no lo puedo responder. Volvamos a la ecuación: ¿en qué parte del ejercicio estás?"
    '<meta>{"ejercicio": null, "tipo_pedido": "conversacion", "escalon": 0, '
    '"error_detectado": null, "estado": "avanzando"}</meta>'
)


class ErrorTutor(Exception):
    """La respuesta del tutor no se pudo obtener (red, cuota, clave)."""


class Responder(Protocol):
    def __call__(self, system: str, mensajes: list[dict]) -> tuple[str, str]: ...


class ClienteClaude:
    def __init__(self, modelo: str, esfuerzo: str, max_tokens: int):
        self.modelo = modelo
        self.esfuerzo = esfuerzo
        self.max_tokens = max_tokens
        self._cliente: anthropic.Anthropic | None = None

    def _obtener_cliente(self) -> anthropic.Anthropic:
        if self._cliente is None:
            self._cliente = anthropic.Anthropic(timeout=120.0, max_retries=2)
        return self._cliente

    def __call__(self, system: str, mensajes: list[dict]) -> tuple[str, str]:
        """Devuelve (texto crudo con <meta>, modelo que respondió)."""
        try:
            respuesta = self._obtener_cliente().beta.messages.create(
                model=self.modelo,
                max_tokens=self.max_tokens,
                # El system prompt es fijo: se cachea, igual que el historial.
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=mensajes,
                cache_control={"type": "ephemeral"},
                output_config={"effort": self.esfuerzo},
                betas=config.BETAS,
                fallbacks=config.FALLBACKS,
            )
        except anthropic.AuthenticationError as e:
            log.error("Clave de la API inválida o ausente: %s", e)
            raise ErrorTutor("autenticacion") from e
        except anthropic.RateLimitError as e:
            log.warning("Límite de uso de la API: %s", e)
            raise ErrorTutor("limite") from e
        except anthropic.APIStatusError as e:
            log.error("Error de la API (%s): %s", e.status_code, e)
            raise ErrorTutor("api") from e
        except anthropic.APIConnectionError as e:
            log.error("Sin conexión con la API: %s", e)
            raise ErrorTutor("conexion") from e
        except anthropic.AnthropicError as e:
            # Por ejemplo, ANTHROPIC_API_KEY sin definir.
            log.error("No se pudo llamar a la API: %s", e)
            raise ErrorTutor("configuracion") from e

        if respuesta.stop_reason == "refusal":
            log.warning("Pedido declinado (%s)", getattr(respuesta.stop_details, "category", None))
            return TEXTO_DECLINADO, respuesta.model

        texto = "".join(b.text for b in respuesta.content if b.type == "text")
        if respuesta.stop_reason == "max_tokens":
            log.warning("Respuesta cortada por max_tokens")
        return texto, respuesta.model
