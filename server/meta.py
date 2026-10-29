"""Extracción del bloque <meta>…</meta> que el tutor pone al final de cada respuesta.

El estudiante nunca ve el bloque: se separa del texto visible, se valida contra el
esquema de tutor/metadatos.md y se guarda en la base.
"""
from __future__ import annotations

import json
import re

TIPOS_PEDIDO = {"orientacion", "respuesta", "verificacion", "conversacion"}
ESTADOS = {"avanzando", "trabado", "resuelto_por_estudiante"}
CODIGOS_ERROR = {f"E{n:02d}" for n in range(1, 11)}

_BLOQUE = re.compile(r"<meta>(.*?)</meta>", re.DOTALL | re.IGNORECASE)
# Un <meta> sin cierre (respuesta cortada): se descarta desde ahí hasta el final.
_ABIERTO = re.compile(r"<meta>.*\Z", re.DOTALL | re.IGNORECASE)
_SUELTA = re.compile(r"</?meta>", re.IGNORECASE)
_CERCO = re.compile(r"^```(?:json)?\s*|\s*```$")


def _validar(datos: object) -> dict | None:
    """Devuelve el meta normalizado, o None si no respeta el esquema."""
    if not isinstance(datos, dict):
        return None
    ejercicio = datos.get("ejercicio")
    tipo = datos.get("tipo_pedido")
    escalon = datos.get("escalon")
    error = datos.get("error_detectado")
    estado = datos.get("estado")

    if ejercicio is not None and not isinstance(ejercicio, str):
        ejercicio = str(ejercicio)
    if tipo not in TIPOS_PEDIDO or estado not in ESTADOS:
        return None
    if isinstance(escalon, bool) or not isinstance(escalon, int) or not 0 <= escalon <= 4:
        return None
    if error is not None and error not in CODIGOS_ERROR:
        return None
    return {
        "ejercicio": ejercicio,
        "tipo_pedido": tipo,
        "escalon": escalon,
        "error_detectado": error,
        "estado": estado,
    }


def extraer(texto_crudo: str) -> dict:
    """Separa el texto visible del metadato.

    Devuelve {"texto", "meta", "meta_json", "meta_valido"}:
    - texto: lo que ve el estudiante, sin ningún rastro de <meta>.
    - meta: dict validado o None.
    - meta_json: el contenido crudo del último bloque (aunque no valide), para revisión.
    """
    bloques = _BLOQUE.findall(texto_crudo)
    visible = _BLOQUE.sub("", texto_crudo)
    visible = _ABIERTO.sub("", visible)
    visible = _SUELTA.sub("", visible).strip()

    meta_json = bloques[-1].strip() if bloques else None
    meta = None
    if meta_json:
        try:
            meta = _validar(json.loads(_CERCO.sub("", meta_json)))
        except (json.JSONDecodeError, ValueError):
            meta = None
    return {"texto": visible, "meta": meta, "meta_json": meta_json, "meta_valido": meta is not None}
