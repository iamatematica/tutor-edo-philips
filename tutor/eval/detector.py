"""Detector de filtraciones de solución y chequeos de forma sobre el texto del tutor.

Lo usan `correr.py` (sobre cada turno del tutor) y `tutor/banco/verificar_banco.py`
(sobre las pistas de cada plantilla). No depende de ningún modelo de lenguaje: toma
cada igualdad que aparece en el texto, la pasa a SymPy y prueba si es solución de
alguna de las ecuaciones en juego derivando y reemplazando.

Una ecuación en juego se describe como F(x, y, p) = 0, donde p = y'.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

TRANSFORMACIONES = standard_transformations + (implicit_multiplication_application, convert_xor)

# Letras que pueden ser la constante de integración en lo que escribe el tutor.
CONSTANTES = ["K", "C", "c", "k", "C_1", "K_1", "C_0", "K_0", "A", "B"]


# ---------------------------------------------------------------------------
# Ecuación en juego
# ---------------------------------------------------------------------------


@dataclass
class Edo:
    """F(indep, funcion, p) = 0 con p = derivada de la función."""

    F: sp.Expr
    indep: sp.Symbol
    funcion: sp.Symbol
    p: sp.Symbol
    nombre: str = ""
    parametros: dict = field(default_factory=dict)

    @classmethod
    def desde_texto(cls, edo: str, indep: str = "x", funcion: str = "y", nombre: str = "", parametros=None):
        parametros = parametros or {}
        x, y, p = sp.Symbol(indep), sp.Symbol(funcion), sp.Symbol("p")
        local = {indep: x, funcion: y, "p": p}
        for k, v in parametros.items():
            local[k] = sp.sympify(v)
        F = parse_expr(edo, local_dict=local, transformations=TRANSFORMACIONES)
        return cls(F=F, indep=x, funcion=y, p=p, nombre=nombre or edo, parametros=parametros)

    def simbolos_libres(self):
        return self.F.free_symbols - {self.indep, self.funcion, self.p}

    def constantes(self):
        """Constantes de integración posibles: las de CONSTANTES que no son parámetros de la EDO."""
        ocupadas = {s.name for s in self.F.free_symbols}
        return [sp.Symbol(c) for c in CONSTANTES if c not in ocupadas]


# ---------------------------------------------------------------------------
# LaTeX (y texto plano) → SymPy
# ---------------------------------------------------------------------------


def _llave(s: str, i: int) -> tuple[str, int]:
    """Devuelve el contenido de la llave que abre en s[i] y el índice siguiente al cierre."""
    assert s[i] == "{"
    nivel = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            nivel += 1
        elif s[j] == "}":
            nivel -= 1
            if nivel == 0:
                return s[i + 1 : j], j + 1
    raise ValueError("llave sin cerrar")


def _argumento(s: str, i: int) -> tuple[str, int]:
    """Argumento de un comando LaTeX: {…} o un solo carácter/token."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        raise ValueError("falta argumento")
    if s[i] == "{":
        return _llave(s, i)
    if s[i] == "\\":
        m = re.match(r"\\[a-zA-Z]+", s[i:])
        return m.group(0), i + len(m.group(0))
    return s[i], i + 1


def _reemplazar_comando(s: str, comando: str, n_args: int, plantilla) -> str:
    patron = re.compile(r"\\" + comando + r"(?![a-zA-Z])")
    while True:
        m = patron.search(s)
        if not m:
            return s
        i = m.end()
        args = []
        for _ in range(n_args):
            a, i = _argumento(s, i)
            args.append(a)
        s = s[: m.start()] + plantilla(*args) + s[i:]


def _parentesis(s: str, i: int) -> tuple[str, int]:
    nivel = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            nivel += 1
        elif s[j] == ")":
            nivel -= 1
            if nivel == 0:
                return s[i + 1 : j], j + 1
    raise ValueError("paréntesis sin cerrar")


def _potencias(s: str) -> str:
    """^{…} → **(…), e^{…} → exp(…)."""
    salida = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "^":
            j = i + 1
            while j < len(s) and s[j] == " ":
                j += 1
            if j < len(s) and s[j] == "{":
                cont, k = _llave(s, j)
            elif j < len(s) and s[j] == "(":
                cont, k = _parentesis(s, j)
            elif j < len(s):
                m = re.match(r"-?[0-9.]+|[a-zA-Z]", s[j:])
                cont, k = (m.group(0), j + len(m.group(0))) if m else (s[j], j + 1)
            else:
                raise ValueError("potencia sin exponente")
            cont = _potencias(cont)
            # e^{…}: la base es la e de Euler si está sola
            previo = "".join(salida)
            if re.search(r"(?:^|[^a-zA-Z_])e\s*$", previo):
                previo = re.sub(r"e\s*$", "", previo)
                salida = [previo, f" exp({cont}) "]
            else:
                salida.append(f"**({cont})")
            i = k
        else:
            salida.append(c)
            i += 1
    return "".join(salida)


def latex_a_texto(s: str) -> str | None:
    """Pasa un lado de una igualdad en LaTeX a sintaxis de SymPy. None si no es una expresión algebraica
    (tiene derivadas, integrales, diferenciales, texto…)."""
    s = s.strip()
    if not s:
        return None
    if re.search(r"\\int|\\prime|'|′|\\to|\\lim|\\sum|\\approx|\\neq|<|>|\\le|\\ge|\\in\b|\\%|%|\\circ|°", s):
        return None
    if re.search(r"(?<![a-zA-Z])d[a-zA-Z](?![a-zA-Z])", s.replace("\\,", " ")):  # dx, dy, dt
        return None
    s = re.sub(r"\\(left|right|big|Big|bigg|Bigg|displaystyle|textstyle)(?![a-zA-Z])", "", s)
    s = re.sub(r"\\(,|;|!|:|quad|qquad| )", " ", s)
    s = re.sub(r"\\(text|mathrm|operatorname|mathit)\s*\{\s*e\s*\}", "e", s)
    s = re.sub(r"\\(text|mbox)\s*\{[^{}]*\}", " ", s)
    s = re.sub(r"\\(mathrm|operatorname|mathit|boldsymbol|mathbf)\s*\{([^{}]*)\}", r"\2", s)
    s = re.sub(r"(\d)\s*\{,\}\s*(\d)", r"\1.\2", s)
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("·", "*").replace("−", "-")
    s = s.replace("\\pm", "+").replace("\\mp", "-").replace("±", "+")
    s = s.replace("\\tau", " tau ").replace("\\lambda", " lambda_ ").replace("\\alpha", " alpha ")
    s = re.sub(r"\\(ln|log)(?![a-zA-Z])", " log ", s)
    s = re.sub(r"\\exp(?![a-zA-Z])", " exp ", s)
    s = re.sub(r"\\(sin|cos|tan)(?![a-zA-Z])", r" \1 ", s)
    try:
        s = _reemplazar_comando(s, "[dt]?frac", 2, lambda a, b: f"(({a})/({b}))")
        s = _reemplazar_comando(s, "sqrt", 1, lambda a: f"sqrt({a})")
    except (ValueError, AttributeError):
        return None
    # subíndices: T_{amb} → T_amb
    s = re.sub(r"_\{\s*([a-zA-Z0-9]+)\s*\}", r"_\1", s)
    # valores absolutos |…| → (…): se trabaja con x > 0
    while "|" in s:
        nuevo = re.sub(r"\|([^|]*)\|", r"(\1)", s, count=1)
        if nuevo == s:
            return None
        s = nuevo
    try:
        s = _potencias(s)
    except ValueError:
        return None
    s = s.replace("{", "(").replace("}", ")")
    if "\\" in s:
        return None
    return s


def a_sympy(texto: str, simbolos: dict) -> sp.Expr | None:
    t = latex_a_texto(texto)
    if t is None:
        return None
    # y(x) → y ; N(t) → N
    for nombre in simbolos:
        if len(nombre) == 1:
            t = re.sub(rf"(?<![a-zA-Z_]){nombre}\s*\(\s*[a-z]\s*\)", nombre, t)
    local = dict(simbolos)
    local.setdefault("e", sp.E)
    local.setdefault("E", sp.Symbol("E"))
    local.setdefault("tau", sp.Symbol("tau"))
    try:
        expr = parse_expr(t, local_dict=local, transformations=TRANSFORMACIONES, evaluate=True)
    except Exception:
        return None
    if not isinstance(expr, sp.Expr):
        return None
    return expr


# ---------------------------------------------------------------------------
# Extracción de igualdades del texto
# ---------------------------------------------------------------------------

RE_META = re.compile(r"<meta>(.*?)</meta>", re.S)
RE_MATE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$|\\\[(.+?)\\\]|\\\((.+?)\\\)", re.S)


def sin_meta(texto: str) -> str:
    return RE_META.sub("", texto).strip()


def leer_meta(texto: str):
    """Devuelve (dict | None, error | None) del último bloque <meta>."""
    bloques = RE_META.findall(texto)
    if not bloques:
        return None, "sin bloque <meta>"
    try:
        return json.loads(bloques[-1].strip()), None
    except json.JSONDecodeError as e:
        return None, f"JSON inválido: {e}"


def segmentos_matematicos(texto: str) -> list[str]:
    return [next(g for g in m.groups() if g is not None) for m in RE_MATE.finditer(texto)]


def texto_sin_matematica(texto: str) -> str:
    return RE_MATE.sub(" ", texto)


def igualdades(segmento: str) -> list[tuple[str, str]]:
    """Pares (izq, der) de igualdades consecutivas en un segmento: a = b = c → (a,b), (b,c)."""
    pares = []
    for parte in re.split(r"\\\\|\\quad|\\qquad|\\Rightarrow|\\Longrightarrow|\\implies|\\to|;|\\text\{\s*(?:o|y|con|donde)\s*\}|\\(?:begin|end)\{[a-z*]+\}|&", segmento):
        lados = re.split(r"(?<![<>!\\])=(?!=)", parte)
        # una coma que separa dos igualdades: "y = 3, \; K = 2"
        for a, b in zip(lados, lados[1:]):
            a = re.split(r"(?<![\\0-9{]),\s*(?![0-9}])", a)[-1]
            b = re.split(r"(?<![\\0-9{]),\s*(?![0-9}])", b)[0]
            if a.strip() and b.strip():
                pares.append((a, b))
    return pares


RE_PLANO = re.compile(r"(?<![\w$])([A-Za-z])\s*(?:\(\s*[a-z]\s*\))?\s*=\s*([^\n;:?¿!¡$]+)")


def igualdades_en_texto_plano(texto: str) -> list[tuple[str, str]]:
    """Igualdades escritas sin $…$ (por ejemplo «y = 3 + K e^(-2x)»)."""
    pares = []
    for m in RE_PLANO.finditer(texto_sin_matematica(sin_meta(texto))):
        der = re.split(r",\s+(?=[A-Za-zÁÉÍÓÚáéíóúñ])", m.group(2))[0].strip().rstrip(".,")
        # cortar cuando empieza prosa
        der = re.split(r"\s(?:y|o|con|donde|que|si|para|es|pero|porque)\s", der)[0]
        if re.search(r"[a-zA-Z]{4,}", re.sub(r"exp|log|sqrt", "", der)):
            continue
        pares.append((m.group(1), der))
    return pares


# ---------------------------------------------------------------------------
# ¿Es solución?
# ---------------------------------------------------------------------------

_rnd = random.Random(20261029)


def _evaluar(expr, valores):
    try:
        v = complex(expr.subs(valores).evalf())
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if v != v or abs(v) == float("inf"):
        return None
    return v


def _anula_numericamente(expr, simbolos, intentos=6) -> bool:
    """expr ≈ 0 en varios puntos al azar (x, y y constantes positivos)."""
    buenos = 0
    for _ in range(intentos * 3):
        valores = {s: _rnd.uniform(0.6, 2.4) for s in simbolos}
        v = _evaluar(expr, valores)
        if v is None:
            continue
        if abs(v) > 1e-7:
            return False
        buenos += 1
        if buenos >= intentos:
            return True
    return buenos >= 3


def _parametros_numericos(edo: Edo, expr):
    """Valores al azar para los parámetros simbólicos de la EDO (k de Newton, etc.)."""
    return {s: sp.Rational(_rnd.randint(2, 9), 7) for s in edo.simbolos_libres()}


def es_solucion_explicita(edo: Edo, f: sp.Expr) -> bool:
    """y = f(x) cumple F(x, f, f') = 0 (derivando y reemplazando). Exige que f dependa de x."""
    if edo.indep not in f.free_symbols or edo.funcion in f.free_symbols or edo.p in f.free_symbols:
        return False
    params = _parametros_numericos(edo, f)
    F = edo.F.subs(params)
    f = f.subs(params)
    residuo = F.subs({edo.p: sp.diff(f, edo.indep)}).subs({edo.funcion: f})
    libres = residuo.free_symbols
    if not libres:
        try:
            return abs(complex(residuo.evalf())) < 1e-9
        except TypeError:
            return False
    return _anula_numericamente(residuo, libres)


def es_solucion_implicita(edo: Edo, G: sp.Expr) -> bool:
    """G(x, y) = 0 define soluciones: derivando implícitamente y' = −G_x / G_y cumple la EDO."""
    x, y = edo.indep, edo.funcion
    if x not in G.free_symbols or y not in G.free_symbols or edo.p in G.free_symbols:
        return False
    params = _parametros_numericos(edo, G)
    F = edo.F.subs(params)
    G = G.subs(params)
    try:
        Gy = sp.diff(G, y)
        if Gy == 0:
            return False
        pend = -sp.diff(G, x) / Gy
    except Exception:
        return False
    residuo = F.subs({edo.p: pend})
    constantes = [c for c in edo.constantes() if c in G.free_symbols]
    if constantes:
        c = constantes[0]
        try:
            despejes = sp.solve(G, c)
        except Exception:
            despejes = []
        if despejes:
            return any(_anula_numericamente(residuo.subs(c, d), residuo.subs(c, d).free_symbols) for d in despejes)
    # sin constante (o no se pudo despejar): una curva concreta → despejar y
    if _anula_numericamente(residuo, residuo.free_symbols):
        return True
    try:
        ramas = sp.solve(G, y)
    except Exception:
        return False
    return any(es_solucion_explicita(edo, r) for r in ramas)


def _normalizar_constantes(expr: sp.Expr, edo: Edo) -> sp.Expr:
    K = sp.Symbol("K")
    return expr.subs({c: K for c in edo.constantes()})


def misma_relacion(edo: Edo, a: tuple[str, sp.Expr], b: tuple[str, sp.Expr]) -> bool:
    """Dos soluciones escritas son la misma (con la constante renombrada)."""
    ta, ea = a
    tb, eb = b
    ea, eb = _normalizar_constantes(ea, edo), _normalizar_constantes(eb, edo)
    libres = (ea.free_symbols | eb.free_symbols) - {edo.p}
    if ta == tb == "explicita":
        return _anula_numericamente(ea - eb, libres) if libres else sp.simplify(ea - eb) == 0
    if ta == tb == "implicita":
        try:
            cociente = sp.simplify(ea / eb)
            if not ({edo.indep, edo.funcion} & cociente.free_symbols):
                return True
            dif = sp.simplify(ea - eb)
            return not ({edo.indep, edo.funcion} & dif.free_symbols)
        except Exception:
            return False
    return False


@dataclass
class Hallazgo:
    edo: str
    igualdad: str
    tipo: str  # explicita | implicita | prohibida
    turno: int | None = None


def clasificar_igualdad(edo: Edo, izq: str, der: str, simbolos: dict):
    """Devuelve (tipo, expr) si la igualdad izq = der es una solución de edo; si no, None."""
    y = edo.funcion
    a = a_sympy(izq, simbolos)
    b = a_sympy(der, simbolos)
    if a is None or b is None:
        return None
    if a == y and es_solucion_explicita(edo, b):
        return ("explicita", b)
    if b == y and es_solucion_explicita(edo, a):
        return ("explicita", a)
    G = a - b
    if y in G.free_symbols and edo.indep in G.free_symbols and not (a == y or b == y):
        if es_solucion_implicita(edo, G):
            return ("implicita", G)
    return None


def simbolos_para(edos: list[Edo]) -> dict:
    sim = {}
    for e in edos:
        for s in e.F.free_symbols | {e.indep, e.funcion}:
            sim[s.name] = s
        for c in e.constantes():
            sim[c.name] = c
    for c in CONSTANTES:
        sim.setdefault(c, sp.Symbol(c))
    return sim


def soluciones_en_texto(texto: str, edos: list[Edo]):
    """Lista de (edo, igualdad, tipo, expr) para cada igualdad del texto que resuelve alguna EDO."""
    sim = simbolos_para(edos)
    visible = sin_meta(texto)
    pares = []
    for seg in segmentos_matematicos(visible):
        pares.extend(igualdades(seg))
    pares.extend(igualdades_en_texto_plano(visible))
    halladas = []
    for izq, der in pares:
        for edo in edos:
            r = clasificar_igualdad(edo, izq, der, sim)
            if r:
                halladas.append((edo, f"{izq.strip()} = {der.strip()}", r[0], r[1]))
    return halladas


def expresiones_prohibidas_en_texto(texto: str, prohibidas: list[str], variable: str = "x"):
    """Resultados prohibidos (p. ej. una integral por partes resuelta): aparecen como lado de una igualdad,
    a menos de una constante aditiva."""
    if not prohibidas:
        return []
    x = sp.Symbol(variable)
    sim = {variable: x, **{c: sp.Symbol(c) for c in CONSTANTES}}
    objetivos = [parse_expr(p, local_dict=sim, transformations=TRANSFORMACIONES) for p in prohibidas]
    visible = sin_meta(texto)
    lados = []
    for seg in segmentos_matematicos(visible):
        lados.extend(l for l in re.split(r"(?<![<>!\\])=", seg) if l.strip())
    hallazgos = []
    for lado in lados:
        e = a_sympy(lado, sim)
        if e is None or x not in e.free_symbols:
            continue
        for obj in objetivos:
            d = sp.diff(e - obj, x)
            libres = d.free_symbols
            if (not libres and abs(complex(d.evalf())) < 1e-9) or (libres and _anula_numericamente(d, libres)):
                hallazgos.append(lado.strip())
                break
    return hallazgos


# ---------------------------------------------------------------------------
# Chequeos de forma (sección 2 del contrato)
# ---------------------------------------------------------------------------

METALENGUAJE = [
    r"escal[oó]n",
    r"andamiaje",
    r"pista\s+(?:de\s+)?nivel",
    r"nivel\s+de\s+(?:la\s+)?pista",
    r"\bP[1-4]\b",
    r"\bE(?:0[1-9]|10)\b",
    r"tipo_pedido",
    r"error_detectado",
    r"metadato",
    r"<\s*/?\s*meta",
]

HERRAMIENTAS_PROHIBIDAS = [r"factor\s+integrante", r"existencia\s+y\s+unicidad", r"teorema\s+de\s+picard"]


def metalenguaje(texto: str) -> list[str]:
    visible = sin_meta(texto)
    return [m.group(0) for p in METALENGUAJE for m in re.finditer(p, visible, re.I)]


def herramientas_prohibidas(texto: str) -> list[str]:
    visible = sin_meta(texto)
    return [m.group(0) for p in HERRAMIENTAS_PROHIBIDAS for m in re.finditer(p, visible, re.I)]


def fracciones_en_linea(texto: str) -> list[str]:
    """Fracciones a/b dentro de la matemática (el contrato pide \\frac)."""
    hallazgos = []
    for seg in segmentos_matematicos(sin_meta(texto)):
        for m in re.finditer(r"[\w\)\}]\s*/\s*[\w\(\{\\]", seg):
            hallazgos.append(seg.strip())
            break
    return hallazgos
