"""Carga e instanciación de las plantillas del banco (un YAML por plantilla).

Lo usan `verificar_banco.py` (verificación con SymPy y armado del catálogo del prompt)
y el corredor de evaluación.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import sympy as sp
import yaml
from sympy.parsing.sympy_parser import parse_expr

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
from detector import TRANSFORMACIONES  # noqa: E402

DIR_BANCO = Path(__file__).resolve().parent
TEMAS = ["clasificacion", "separables", "singular", "lineales", "homogeneas", "fisica"]
CODIGOS = {f"E{n:02d}" for n in range(1, 11)}
CAMPOS_OBLIGATORIOS = ["id", "tema", "nivel", "enunciado", "rango_parametros", "errores_esperados", "pistas"]


def cargar_plantillas(directorio: Path = DIR_BANCO) -> list[dict]:
    plantillas = []
    for ruta in sorted(directorio.glob("*.yaml")):
        with open(ruta, encoding="utf-8") as f:
            datos = yaml.safe_load(f)
        datos["_archivo"] = ruta.name
        plantillas.append(datos)
    return plantillas


def _valor(v):
    if isinstance(v, str):
        return sp.Rational(v) if re.fullmatch(r"-?\d+(/\d+)?|-?\d*\.\d+", v.strip()) else sp.sympify(v)
    return sp.nsimplify(v)


def instancias(plantilla: dict) -> list[dict]:
    """Valores de los parámetros: producto cartesiano (dict de listas) o lista explícita de combinaciones.
    Agrega los `derivados`."""
    rango = plantilla.get("rango_parametros") or {}
    if isinstance(rango, dict):
        nombres = list(rango)
        combinaciones = [dict(zip(nombres, vals)) for vals in itertools.product(*(rango[n] for n in nombres))]
    else:
        combinaciones = [dict(c) for c in rango]
    if not combinaciones:
        combinaciones = [{}]
    salida = []
    for c in combinaciones:
        valores = {k: _valor(v) for k, v in c.items()}
        for nombre, expr in (plantilla.get("derivados") or {}).items():
            valores[nombre] = sp.nsimplify(expr_sympy(expr, valores, plantilla))
        salida.append(valores)
    return salida


def simbolos_de(plantilla: dict) -> dict:
    v = plantilla.get("variables") or {}
    nombres = [v.get("independiente", "x"), v.get("funcion", "y"), "p", "y1", "y2", "y3", "K"]
    sim = {n: sp.Symbol(n) for n in nombres}
    for n in plantilla.get("parametros_simbolicos") or []:
        sim[n] = sp.Symbol(n, positive=True)
    return sim


def expr_sympy(texto: str, valores: dict, plantilla: dict) -> sp.Expr:
    local = simbolos_de(plantilla)
    local.update({k: v for k, v in valores.items()})
    local.setdefault("sol", sp.Function("sol"))
    return parse_expr(str(texto), local_dict=local, transformations=TRANSFORMACIONES)


# ---------------------------------------------------------------------------
# Texto con [[parámetros]]
# ---------------------------------------------------------------------------


def _decimal(v) -> str:
    fr = Fraction(int(sp.fraction(v)[0]), int(sp.fraction(v)[1]))
    texto = f"{float(fr):.10f}".rstrip("0").rstrip(".")
    return texto.replace(".", "{,}")


def formatear(v, filtro: str | None) -> str:
    v = sp.nsimplify(v)
    if filtro == "dec":
        return _decimal(v)
    if filtro == "coef":
        if v == 1:
            return ""
        if v == -1:
            return "-"
    if v.is_Rational and v.q != 1:
        signo = "-" if v < 0 else ""
        return f"{signo}\\frac{{{abs(v.p)}}}{{{v.q}}}"
    return str(v)


def render(texto: str, valores: dict) -> str:
    def sustituir(m):
        nombre, _, filtro = m.group(1).partition("|")
        return formatear(valores[nombre.strip()], filtro.strip() or None)

    return re.sub(r"\[\[([^\]]+)\]\]", sustituir, str(texto)).strip()


@dataclass
class Instancia:
    plantilla: dict
    valores: dict

    @property
    def id(self):
        return self.plantilla["id"]

    def texto(self, campo: str) -> str:
        return render(self.plantilla[campo], self.valores)

    def pistas(self) -> dict:
        return {k: render(v, self.valores) for k, v in self.plantilla["pistas"].items()}
