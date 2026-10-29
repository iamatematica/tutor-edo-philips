"""Tutor guionado del modo demostración (TUTOR_DEMO=1): sin API, sin costo.

Reemplaza a ClienteClaude con la misma interfaz (system, mensajes) → (texto, modelo).
No es una IA: sigue un guion con las plantillas del banco (tutor/banco/*.yaml).

- Propone solo ejercicios del banco, con los números de su primera instancia.
- Escalera P1 → P4 de la plantilla, un escalón por pedido («Pista», «ayuda», «no sé
  seguir»…). Después de P4 no avanza: repite lo planteado y pide el intento.
- A un intento le contesta con un comentario genérico que no dice si está bien ni
  cuál es la respuesta: lo manda a verificar derivando y reemplazando.
- Si el estudiante trae una ecuación que no está en el banco, le propone una del banco.
- Termina cada respuesta con el <meta> del esquema de tutor/metadatos.md.

No guarda estado: como el tutor real, se orienta con los últimos turnos de la sesión
que le pasa el server. Reconoce sus propias respuestas porque contienen el enunciado,
las pistas o la ecuación de la instancia en curso.
"""
from __future__ import annotations

import ast
import itertools
import json
import operator
import re
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

MODELO_DEMO = "demo-guionado"
ORDEN_TEMAS = ["separables", "lineales", "homogeneas", "fisica", "singular", "clasificacion"]


# ---------------------------------------------------------------------------
# Banco: carga e instanciación sin SymPy (el server no lo instala).
# Mismo formato de salida que tutor/banco/banco.py:render (un test lo compara).
# ---------------------------------------------------------------------------

_OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.Pow: operator.pow}


def _evaluar(expr: str, valores: dict[str, Fraction]) -> Fraction:
    """Aritmética racional de los `derivados` (R*C, 4*a**2, E/L…)."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return Fraction(str(n.value))
        if isinstance(n, ast.Name):
            return valores[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPERADORES:
            return Fraction(_OPERADORES[type(n.op)](ev(n.left), ev(n.right)))
        raise ValueError(f"Expresión no admitida en el banco: {expr}")
    return ev(ast.parse(str(expr), mode="eval"))


def _formatear(v: Fraction, filtro: str | None) -> str:
    if filtro == "dec":
        return f"{float(v):.10f}".rstrip("0").rstrip(".").replace(".", "{,}")
    if filtro == "coef":
        if v == 1:
            return ""
        if v == -1:
            return "-"
    if v.denominator != 1:
        signo = "-" if v < 0 else ""
        return f"{signo}\\frac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return str(v.numerator)


def render(texto: str, valores: dict[str, Fraction]) -> str:
    def sustituir(m):
        nombre, _, filtro = m.group(1).partition("|")
        return _formatear(valores[nombre.strip()], filtro.strip() or None)
    return re.sub(r"\[\[([^\]]+)\]\]", sustituir, str(texto)).strip()


def _combinaciones(plantilla: dict) -> list[dict[str, Fraction]]:
    rango = plantilla.get("rango_parametros") or {}
    if isinstance(rango, dict):
        nombres = list(rango)
        combos = [dict(zip(nombres, vals)) for vals in itertools.product(*(rango[n] for n in nombres))]
    else:
        combos = [dict(c) for c in rango]
    salida = []
    for c in combos or [{}]:
        valores = {k: Fraction(str(v)) for k, v in c.items()}
        for nombre, expr in (plantilla.get("derivados") or {}).items():
            valores[nombre] = _evaluar(expr, valores)
        salida.append(valores)
    return salida


@dataclass
class Ejercicio:
    """Una instancia de una plantilla, con sus textos ya armados."""
    id: str
    tema: str
    enunciado: str
    ecuacion: str          # el primer $…$ del enunciado que tiene una derivada
    pistas: list[str]      # P1 … P4


def _ecuacion(enunciado: str) -> str:
    for m in re.finditer(r"\$[^$]+\$", enunciado):
        if "'" in m.group(0):
            return m.group(0)
    return ""


def cargar_banco(directorio: Path) -> list[Ejercicio]:
    """Todas las instancias del banco, ordenadas por tema y por id."""
    ejercicios = []
    for ruta in sorted(Path(directorio).glob("*.yaml")):
        with open(ruta, encoding="utf-8") as f:
            p = yaml.safe_load(f)
        for valores in _combinaciones(p):
            enunciado = render(p["enunciado"], valores)
            ejercicios.append(Ejercicio(
                id=p["id"], tema=p["tema"], enunciado=enunciado, ecuacion=_ecuacion(enunciado),
                pistas=[render(p["pistas"][f"P{n}"], valores) for n in range(1, 5)],
            ))
    if not ejercicios:
        raise RuntimeError(f"No hay plantillas en {directorio}")
    orden = {t: i for i, t in enumerate(ORDEN_TEMAS)}
    ejercicios.sort(key=lambda e: (orden.get(e.tema, 99), e.id))
    return ejercicios


# ---------------------------------------------------------------------------
# Lectura del mensaje del estudiante
# ---------------------------------------------------------------------------

def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def normalizar_ecuacion(texto: str) -> str:
    """Forma canónica para comparar la ecuación del estudiante con las del banco."""
    t = texto.replace("$", "").replace("′", "'").replace("’", "'").replace("−", "-")
    t = re.sub(r"\\frac\{d(\w)\}\{d\w\}", r"\1'", t)
    t = re.sub(r"\bd(\w)/d\w\b", r"\1'", t)
    t = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", t)
    t = re.sub(r"\\(cdot|left|right|,|;|!|quad)|\\ |[\s*{}·]", "", t)
    t = t.replace("{,}", ".").replace(",", ".")
    t = re.sub(r"\((\w+)\)", r"\1", t)  # (2x+y)/x y 2x+y/x no se distinguen: alcanza para comparar
    return t.lower()


_RE_DERIVADA = re.compile(r"[A-Za-z]\s*(?:'|′|’)|\\frac\{d\w\}\{d\w\}|\bd\w\s*/\s*d\w\b")
_RE_PISTA = re.compile(r"\b(pista|ayuda|ayudame|ayudarme|no se( como)?|no entiendo|como sigo|"
                       r"me trabe|trabad[oa]|no me sale|que hago)\b")
_RE_RESPUESTA = re.compile(r"\b(respuesta|resolve(lo|la|me|melo)|(dame|pasame|decime) la solucion|"
                           r"solucion (completa|final)|pasame(lo|la)?|decime (cuanto|que) (da|queda)|"
                           r"cuanto da|hace(lo|la|melo))\b")
_RE_OTRO = re.compile(r"\b(otro|otra|siguiente|nuevo|cambiar|cambio)\b.*\b(ejercicio|ecuacion|problema)\b|"
                      r"^\s*(otro|otra|siguiente)\b")
_RE_PIDE_EJERCICIO = re.compile(r"\b(ejercicio|proponeme|propone|quiero practicar|dame uno|practicar)\b")
_RE_INTENTO = re.compile(r"\b(me (da|dio|quedo|sale|salio)|llegue|tengo|obtuve|hice|derive|integre|"
                         r"quedaria|seria)\b|=")
TEMAS_PEDIDOS = [
    ("lineales", r"\blineal"), ("homogeneas", r"homogene"), ("separables", r"separab"),
    ("fisica", r"fisica|circuito|capacitor|newton|enfriamiento|desintegr|caida|rl\b|rc\b"),
    ("singular", r"singular"), ("clasificacion", r"clasific|orden|grado"),
]


def _tema_parecido(texto: str) -> str:
    """Tema del banco que más se parece a una ecuación que no está en el banco."""
    t = texto.replace(" ", "")
    if "''" in t or "^{" in t and "(y')" in t:
        return "clasificacion"
    if re.search(r"\(y'\)\^?\{?2", t):
        return "singular"
    if re.search(r"[A-Za-z]'[+-]\d*[A-Za-z]", t):
        return "lineales"
    if re.search(r"/x|\\frac\{[^}]*y[^}]*\}\{x", t) and "y" in t:
        return "homogeneas"
    return "separables"


# ---------------------------------------------------------------------------
# Tutor guionado
# ---------------------------------------------------------------------------

def _meta(ejercicio: str | None, tipo: str, escalon: int = 0, estado: str = "avanzando") -> str:
    datos = {"ejercicio": ejercicio, "tipo_pedido": tipo, "escalon": escalon,
             "error_detectado": None, "estado": estado}
    return "<meta>" + json.dumps(datos, ensure_ascii=False) + "</meta>"


class TutorGuionado:
    """Tutor sin IA para el modo demostración. Misma interfaz que ClienteClaude."""

    def __init__(self, banco: Path):
        self.ejercicios = cargar_banco(banco)
        # Una instancia (la primera) por plantilla para proponer.
        self.propuestas: list[Ejercicio] = []
        for e in self.ejercicios:
            if all(p.id != e.id for p in self.propuestas):
                self.propuestas.append(e)
        self._por_ecuacion: dict[str, Ejercicio] = {}
        for e in self.ejercicios:
            if e.ecuacion:
                self._por_ecuacion.setdefault(normalizar_ecuacion(e.ecuacion), e)

    # ---------- estado a partir de la conversación ----------

    def _huellas(self, texto: str) -> dict[int, tuple[int, bool]]:
        """Instancias que aparecen en una respuesta del tutor: índice → (pista más alta, ¿la propuso?)."""
        encontradas = {}
        for i, e in enumerate(self.ejercicios):
            propuesta = e.enunciado in texto
            pista = max((n for n, p in enumerate(e.pistas, 1) if p in texto), default=0)
            if propuesta or pista or (e.ecuacion and e.ecuacion in texto):
                encontradas[i] = (pista, propuesta)
        return encontradas

    def estado(self, mensajes: list[dict]) -> tuple[Ejercicio | None, int]:
        """Ejercicio en curso y última pista dada, leyendo las respuestas anteriores."""
        candidatos: set[int] | None = None
        escalon = 0
        for m in reversed(mensajes):
            if m["role"] != "assistant":
                continue
            huellas = self._huellas(m["content"])
            if not huellas:
                continue
            if candidatos is None:
                candidatos = set(huellas)
            elif candidatos & set(huellas):
                candidatos &= set(huellas)
            else:
                break  # una respuesta de otro ejercicio: de ahí para atrás ya no cuenta
            escalon = max([escalon] + [huellas[i][0] for i in candidatos])
            if any(huellas[i][1] for i in candidatos):
                break  # acá se propuso el ejercicio en curso
        if not candidatos:
            return None, 0
        return self.ejercicios[min(candidatos)], escalon

    # ---------- respuestas ----------

    def _proponer(self, actual: Ejercicio | None, tema: str | None = None) -> Ejercicio:
        if tema:
            del_tema = [e for e in self.propuestas if e.tema == tema and (not actual or e.id != actual.id)]
            if del_tema:
                return del_tema[0]
        if actual is None:
            return self.propuestas[0]
        i = next((k for k, e in enumerate(self.propuestas) if e.id == actual.id), -1)
        return self.propuestas[(i + 1) % len(self.propuestas)]

    def _pista(self, ej: Ejercicio, escalon: int, previa_fue_pista: bool, tipo: str, intro: str = "") -> str:
        estado = "trabado" if previa_fue_pista else "avanzando"
        if escalon >= 4:
            texto = (f"{intro}Desde acá el paso es tuyo. Volvé a lo último que quedó: {ej.pistas[3]}\n\n"
                     "Escribí tu intento, aunque no estés seguro, y lo miramos juntos.")
            return texto + _meta(ej.id, tipo, 4, estado)
        return f"{intro}{ej.pistas[escalon]}" + _meta(ej.id, tipo, escalon + 1, estado)

    def _comentar_intento(self, ej: Ejercicio, mensajes: list[dict]) -> str:
        intentos = sum(1 for m in mensajes[:-1] if m["role"] == "user" and _RE_INTENTO.search(_plano(m["content"])))
        if ej.tema == "clasificacion":
            comentarios = [
                f"Bien que lo escribas. Revisá que tu respuesta diga las tres cosas para {ej.ecuacion}: "
                "orden, grado y si es lineal. ¿De qué derivada sacaste el grado?",
                f"Mirá de nuevo {ej.ecuacion}: ¿el exponente que usaste para el grado es el de la derivada "
                "más alta o el de otra?",
            ]
        else:
            comentarios = [
                "Bien que lo escribas. Para saber si está bien no necesitás que te lo diga yo: derivá tu "
                f"resultado y reemplazalo en {ej.ecuacion}. Si los dos miembros quedan iguales, está. ¿Qué te dio?",
                f"Revisalo paso a paso: ¿dónde apareció la constante y qué le pasó al despejar? Después "
                f"comprobalo derivando y reemplazando en {ej.ecuacion}.",
                "¿Usaste la condición inicial recién al final, con la solución general ya despejada? "
                f"Cuando lo tengas, derivá y reemplazá en {ej.ecuacion} para comprobarlo.",
            ]
        return comentarios[intentos % len(comentarios)] + _meta(ej.id, "verificacion", 0)

    def responder(self, mensajes: list[dict]) -> str:
        texto = mensajes[-1]["content"].strip()
        plano = _plano(texto)
        actual, escalon = self.estado(mensajes[:-1])
        previo = [m for m in mensajes[:-1] if m["role"] == "user"]
        previa_fue_pista = bool(previo) and bool(_RE_PISTA.search(_plano(previo[-1]["content"])))

        es_pista = texto == "Pista" or bool(_RE_PISTA.search(plano))
        pide_respuesta = bool(_RE_RESPUESTA.search(plano))
        tiene_derivada = bool(_RE_DERIVADA.search(texto)) and "=" in texto
        tema_pedido = next((t for t, rx in TEMAS_PEDIDOS if re.search(rx, plano)), None)

        # 1. Pide la respuesta (E10): no se da; a lo sumo, la pista siguiente.
        if pide_respuesta:
            if actual is None:
                ej = self._proponer(None)
                return (f"La respuesta no te la voy a pasar, pero te acompaño a que llegues. Empecemos con uno "
                        f"del curso: {ej.enunciado} ¿Por dónde arrancarías?" + _meta(ej.id, "respuesta", 0))
            return self._pista(actual, escalon, previa_fue_pista, "respuesta",
                               "La respuesta no te la voy a pasar: la idea es que llegues vos, y llegás. ")

        # 2. Pista (botón o pedido de ayuda).
        if es_pista and not tiene_derivada:
            if actual is None:
                ej = self._proponer(None, tema_pedido)
                return (f"Arranquemos con uno del curso: {ej.enunciado}\n\n{ej.pistas[0]}"
                        + _meta(ej.id, "orientacion", 1))
            return self._pista(actual, escalon, previa_fue_pista, "orientacion")

        # 3. Pide otro ejercicio, o uno de un tema.
        if _RE_OTRO.search(plano) or (_RE_PIDE_EJERCICIO.search(plano) and not tiene_derivada):
            ej = self._proponer(actual, tema_pedido)
            return f"Dale. Probá con este: {ej.enunciado} ¿Por dónde arrancarías?" + _meta(ej.id, "conversacion", 0)

        # 4. Escribe una ecuación diferencial: si es del banco, arranca; si no, se propone una del banco.
        #    Con un ejercicio en curso, una igualdad con y' puede ser parte de su intento.
        if tiene_derivada:
            del_banco = self._por_ecuacion.get(normalizar_ecuacion(texto.split(":")[-1]))
            if del_banco is None:
                for parte in re.findall(r"\$[^$]+\$", texto):
                    del_banco = del_banco or self._por_ecuacion.get(normalizar_ecuacion(parte))
            if del_banco is not None and actual is not None and del_banco.id == actual.id:
                return (f"Sí, es el que venimos trabajando: {actual.ecuacion}. ¿En qué parte estás? "
                        "Si te trabaste, tocá «Pista»." + _meta(actual.id, "conversacion", 0))
            if del_banco is not None:
                return (f"Ese está entre los ejercicios del curso: {del_banco.enunciado}\n\n{del_banco.pistas[0]}"
                        + _meta(del_banco.id, "orientacion", 1))
            if del_banco is None and (actual is None or not _RE_INTENTO.search(plano.replace("=", ""))):
                ej = self._proponer(None, _tema_parecido(texto))
                return ("Esa ecuación no está entre los ejercicios que preparó tu profe para este chat, así que "
                        f"acá no la vamos a resolver. Te propongo una parecida del curso: {ej.enunciado} "
                        "¿Por dónde arrancarías?" + _meta(ej.id, "conversacion", 0))

        # 5. Un intento sobre el ejercicio en curso.
        if actual is not None and _RE_INTENTO.search(plano):
            return self._comentar_intento(actual, mensajes)

        # 6. Cualquier otra cosa: saludo, fuera de tema, teoría.
        if actual is None:
            ej = self._proponer(None, tema_pedido)
            return ("¡Hola! Acá trabajamos ecuaciones diferenciales de primer orden. Te propongo empezar con "
                    f"este: {ej.enunciado} ¿Por dónde arrancarías? Si no sabés, tocá «Pista»."
                    + _meta(ej.id, "conversacion", 0))
        return (f"Eso queda para otro momento. Sigamos con {actual.ecuacion}: ¿en qué parte estás? "
                "Si te trabaste, tocá «Pista»." + _meta(actual.id, "conversacion", 0))

    def __call__(self, system: str, mensajes: list[dict]) -> tuple[str, str]:
        return self.responder(mensajes), MODELO_DEMO
