"""Verifica todas las plantillas del banco con SymPy.

    python tutor/banco/verificar_banco.py                    # verifica; sale con código 1 si hay fallos
    python tutor/banco/verificar_banco.py --actualizar-prompt  # además reescribe el catálogo en system_prompt.md

Para cada plantilla y cada instancia de sus parámetros:
  - deriva la solución general y la reemplaza en la ecuación (simplify(lhs − rhs) == 0);
  - comprueba la condición inicial y que la particular salga de la general;
  - en singulares, que la singular cumpla la ecuación y no salga de la general para ningún K;
  - en homogéneas, el grado 0: F(λx, λy) − F(x, y) == 0;
  - en física, la forma y' + a·y = b, el valor final b/a, la constante de tiempo 1/a y los controles;
  - en clasificación, orden, grado y linealidad;
  - que las pistas no filtren la solución, no usen metalenguaje ni fracciones en línea,
    y que el enunciado no sea una de las ecuaciones a evitar (sección 4 del contrato).
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from pathlib import Path

import sympy as sp

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent / "eval"))

from banco import (  # noqa: E402
    CAMPOS_OBLIGATORIOS,
    CODIGOS,
    TEMAS,
    Instancia,
    cargar_plantillas,
    expr_sympy,
    instancias,
    simbolos_de,
)
from detector import (  # noqa: E402
    Edo,
    es_solucion_explicita,
    es_solucion_implicita,
    fracciones_en_linea,
    herramientas_prohibidas,
    metalenguaje,
    soluciones_en_texto,
)

PROMPT = AQUI.parent / "system_prompt.md"
INICIO, FIN = "<!-- BANCO:INICIO -->", "<!-- BANCO:FIN -->"

# Ecuaciones que la sección 4 manda evitar (sobre el enunciado ya instanciado).
EVITAR = [
    (r"y'\s*\+\s*y\s*=\s*x(?![\w^{])", "y' + y = x exige integración por partes"),
    (r"y'\s*=\s*2\s*\\sqrt\{\s*y\s*\}", "y' = 2√y arrastra la restricción x ≥ −C"),
]

_rnd = random.Random(7)


def es_cero(expr, simbolos_positivos=()) -> bool:
    """simplify(expr) == 0, con respaldo numérico (valores positivos al azar)."""
    try:
        if sp.simplify(expr) == 0:
            return True
    except Exception:
        pass
    libres = list(expr.free_symbols)
    if not libres:
        try:
            return abs(complex(expr.evalf())) < 1e-10
        except TypeError:
            return False
    for _ in range(8):
        v = {s: _rnd.uniform(0.6, 2.4) for s in libres}
        try:
            if abs(complex(expr.subs(v).evalf())) > 1e-9:
                return False
        except (TypeError, ZeroDivisionError):
            return False
    return True


class Verificador:
    def __init__(self):
        self.fallos: list[str] = []
        self.chequeos = 0

    def check(self, condicion: bool, mensaje: str):
        self.chequeos += 1
        if not condicion:
            self.fallos.append(mensaje)

    # -- estructura ---------------------------------------------------------

    def estructura(self, p: dict):
        pid = p.get("id", p["_archivo"])
        for campo in CAMPOS_OBLIGATORIOS:
            self.check(campo in p, f"{pid}: falta el campo `{campo}`")
        self.check(p.get("tema") in TEMAS, f"{pid}: tema desconocido {p.get('tema')!r}")
        self.check(isinstance(p.get("nivel"), int) and 1 <= p["nivel"] <= 5, f"{pid}: nivel fuera de 1–5")
        errores = p.get("errores_esperados") or []
        self.check(bool(errores), f"{pid}: sin errores_esperados")
        for e in errores:
            self.check(e in CODIGOS and e != "E10", f"{pid}: código de error inválido {e}")
        pistas = p.get("pistas") or {}
        self.check(list(pistas) == ["P1", "P2", "P3", "P4"], f"{pid}: las pistas tienen que ser P1, P2, P3, P4 en orden")
        if p.get("tema") != "clasificacion":
            self.check("edo" in p and ("solucion_general" in p or "solucion_general_implicita" in p),
                       f"{pid}: falta edo o solucion_general")
            if p.get("condicion_inicial"):
                self.check("solucion_particular" in p or "solucion_particular_implicita" in p,
                           f"{pid}: tiene condición inicial pero no solucion_particular")
        if p.get("tema") == "fisica":
            self.check("enunciado_planteo" in p, f"{pid}: física sin ítem que pida plantear la ecuación")
        self.check(p["_archivo"] == f"{pid}.yaml", f"{pid}: el archivo tiene que llamarse {pid}.yaml")

    # -- textos -------------------------------------------------------------

    def textos(self, inst: Instancia, edo: Edo | None, etiqueta: str):
        p = inst.plantilla
        campos = ["enunciado"] + (["enunciado_planteo"] if "enunciado_planteo" in p else [])
        enunciados = [inst.texto(c) for c in campos]
        for c, t in zip(campos, enunciados):
            self.check("[[" not in t, f"{etiqueta}: parámetro sin reemplazar en {c}")
            self.check(not fracciones_en_linea(t), f"{etiqueta}: fracción en línea en {c}: {fracciones_en_linea(t)}")
            self.check(not herramientas_prohibidas(t), f"{etiqueta}: herramienta prohibida en {c}")
            self.check(not metalenguaje(t), f"{etiqueta}: metalenguaje en {c}: {metalenguaje(t)}")
            for patron, motivo in EVITAR:
                self.check(not re.search(patron, t), f"{etiqueta}: {c} usa una ecuación a evitar ({motivo})")
        dadas = []
        if edo is not None:
            for t in enunciados:
                dadas += [h[3] for h in soluciones_en_texto(t, [edo])]
        for nombre, texto in inst.pistas().items():
            self.check("[[" not in texto, f"{etiqueta} {nombre}: parámetro sin reemplazar")
            self.check(not metalenguaje(texto), f"{etiqueta} {nombre}: metalenguaje {metalenguaje(texto)}")
            self.check(not fracciones_en_linea(texto), f"{etiqueta} {nombre}: fracción en línea")
            self.check(not herramientas_prohibidas(texto), f"{etiqueta} {nombre}: herramienta prohibida")
            if edo is not None:
                filtradas = [h for h in soluciones_en_texto(texto, [edo])
                             if not any(es_cero(sp.expand(h[3] - d)) for d in dadas)]
                self.check(not filtradas, f"{etiqueta} {nombre}: la pista filtra una solución: {[h[1] for h in filtradas]}")

    # -- matemática ---------------------------------------------------------

    def clasificacion(self, inst: Instancia, etiqueta: str):
        p, v = inst.plantilla, inst.valores
        F = expr_sympy(p["edo"], v, p)
        sim = simbolos_de(p)
        derivs = [sim["y1"], sim["y2"], sim["y3"]]
        presentes = [i + 1 for i, d in enumerate(derivs) if d in F.free_symbols]
        orden = max(presentes)
        mayor = derivs[orden - 1]
        poly = sp.Poly(F, *derivs, sim["y"])
        grado = sp.degree(F, mayor)
        lineal = poly.total_degree() <= 1
        esperado = p["clasificacion"]
        self.check(orden == int(expr_sympy(str(esperado["orden"]), v, p)), f"{etiqueta}: orden {orden} ≠ {esperado['orden']}")
        self.check(grado == int(expr_sympy(str(esperado["grado"]), v, p)), f"{etiqueta}: grado {grado} ≠ {esperado['grado']}")
        self.check(lineal == bool(esperado["lineal"]), f"{etiqueta}: lineal {lineal} ≠ {esperado['lineal']}")

    def edo_de(self, inst: Instancia) -> Edo:
        p, v = inst.plantilla, inst.valores
        sim = simbolos_de(p)
        var = p.get("variables") or {}
        x, y = sim[var.get("independiente", "x")], sim[var.get("funcion", "y")]
        return Edo(F=expr_sympy(p["edo"], v, p), indep=x, funcion=y, p=sim["p"], nombre=inst.texto("enunciado"))

    def ecuacion(self, inst: Instancia, etiqueta: str) -> Edo:
        p, v = inst.plantilla, inst.valores
        edo = self.edo_de(inst)
        x, y, pp = edo.indep, edo.funcion, edo.p
        K = sp.Symbol("K")

        def residuo(f):
            return edo.F.subs(pp, sp.diff(f, x)).subs(y, f)

        general = None
        if "solucion_general" in p:
            general = expr_sympy(p["solucion_general"], v, p)
            self.check(K in general.free_symbols and sp.diff(general, K) != 0, f"{etiqueta}: la general no depende de K")
            self.check(es_cero(residuo(general)), f"{etiqueta}: la general no cumple la ecuación (derivar y reemplazar)")
        if "solucion_general_implicita" in p:
            G = expr_sympy(p["solucion_general_implicita"], v, p)
            self.check(K in G.free_symbols, f"{etiqueta}: la general implícita no tiene K")
            self.check(es_solucion_implicita(edo, G), f"{etiqueta}: la general implícita no cumple la ecuación")

        ci = p.get("condicion_inicial")
        if ci:
            x0 = expr_sympy(str(ci["x0"]), v, p)
            y0 = expr_sympy(str(ci["y0"]), v, p)
            particulares = p.get("solucion_particular")
            if particulares is not None:
                particulares = particulares if isinstance(particulares, list) else [particulares]
                for s in particulares:
                    f = expr_sympy(s, v, p)
                    self.check(es_cero(residuo(f)), f"{etiqueta}: la particular {s} no cumple la ecuación")
                    self.check(es_cero(f.subs(x, x0) - y0), f"{etiqueta}: la particular {s} no cumple la condición inicial")
                    if general is not None:
                        ks = sp.solve(sp.Eq(general.subs(x, x0), y0), K)
                        self.check(any(es_cero(general.subs(K, k) - f) for k in ks),
                                   f"{etiqueta}: la particular {s} no sale de la general")
            if "solucion_particular_implicita" in p:
                G = expr_sympy(p["solucion_particular_implicita"], v, p)
                self.check(es_cero(G.subs({x: x0, y: y0})), f"{etiqueta}: la particular implícita no pasa por la condición inicial")
                # una curva sin constante: se despeja y se prueba cada rama
                ramas = sp.solve(G, y)
                self.check(any(es_cero(residuo(r)) for r in ramas), f"{etiqueta}: la particular implícita no cumple la ecuación")

        if "solucion_singular" in p:
            s = expr_sympy(p["solucion_singular"], v, p)
            self.check(es_cero(residuo(s)), f"{etiqueta}: la singular no cumple la ecuación")
            if general is not None:
                # ¿existe K tal que general ≡ singular? Se despeja K en un punto y se prueba en otros.
                ks = sp.solve(sp.Eq(general.subs(x, sp.Rational(1, 3)), s.subs(x, sp.Rational(1, 3))), K)
                sale = any(es_cero(general.subs(K, k) - s) for k in ks)
                self.check(not sale, f"{etiqueta}: la «singular» sale de la general")

        if p.get("tema") == "homogeneas":
            f = expr_sympy(p["f_homogenea"], v, p)
            lam = sp.Symbol("lambda", positive=True)
            self.check(es_cero(f.subs({x: lam * x, y: lam * y}, simultaneous=True) - f), f"{etiqueta}: F no es de grado 0")
            self.check(es_cero(edo.F - (pp - f)), f"{etiqueta}: la edo no es y' = F(x, y)")

        if p.get("tema") == "fisica":
            self.fisica(inst, edo, etiqueta)
        return edo

    def fisica(self, inst: Instancia, edo: Edo, etiqueta: str):
        p, v = inst.plantilla, inst.valores
        y, pp, t = edo.funcion, edo.p, edo.indep
        F = sp.expand(edo.F / edo.F.coeff(pp))
        a = F.coeff(y)
        b = -(F - pp - a * y)
        self.check(not ({y, pp, t} & (a.free_symbols | b.free_symbols)), f"{etiqueta}: no tiene la forma y' + a·y = b con a, b constantes")
        control = p.get("control") or {}
        if "valor_final" in control:
            self.check(es_cero(b / a - expr_sympy(str(control["valor_final"]), v, p)), f"{etiqueta}: valor final ≠ b/a")
        if "tau" in control:
            self.check(es_cero(1 / a - expr_sympy(str(control["tau"]), v, p)), f"{etiqueta}: constante de tiempo ≠ 1/a")
        if p.get("solucion_particular") and not isinstance(p["solucion_particular"], list):
            sol = sp.Lambda(t, expr_sympy(p["solucion_particular"], v, p))
            for c in p.get("controles") or []:
                e = expr_sympy(c["cero"], v, p).replace(sp.Function("sol"), sol)
                self.check(es_cero(e), f"{etiqueta}: falla el control «{c['descripcion']}»")

    # -- todo ---------------------------------------------------------------

    def plantilla(self, p: dict) -> int:
        self.estructura(p)
        n = 0
        for i, valores in enumerate(instancias(p)):
            inst = Instancia(p, valores)
            etiqueta = f"{p['id']}#{i + 1} {valores}"
            try:
                if p["tema"] == "clasificacion":
                    self.clasificacion(inst, etiqueta)
                    edo = None
                else:
                    edo = self.ecuacion(inst, etiqueta)
                self.textos(inst, edo, etiqueta)
            except Exception as e:  # una excepción es un fallo, no un corte
                self.check(False, f"{etiqueta}: excepción {type(e).__name__}: {e}")
            n += 1
        return n


# ---------------------------------------------------------------------------
# Catálogo para el system prompt
# ---------------------------------------------------------------------------

NOMBRE_TEMA = {
    "clasificacion": "Clasificación",
    "separables": "Variables separables",
    "singular": "Solución singular",
    "lineales": "Lineales de primer orden (y = u·v)",
    "homogeneas": "Homogéneas",
    "fisica": "Aplicaciones a la Física",
}


def catalogo(plantillas: list[dict], max_instancias: int = 4) -> str:
    lineas = [
        INICIO,
        "<!-- Generado por `python tutor/banco/verificar_banco.py --actualizar-prompt`. No editar a mano. -->",
        "",
    ]
    for tema in TEMAS:
        lineas.append(f"### {NOMBRE_TEMA[tema]}")
        lineas.append("")
        for p in [q for q in plantillas if q["tema"] == tema]:
            todas = instancias(p)
            m = min(max_instancias, len(todas))
            indices = sorted({round(i * (len(todas) - 1) / max(m - 1, 1)) for i in range(m)})
            elegidas = [todas[i] for i in indices]
            lineas.append(f"**{p['id']}** · nivel {p['nivel']} · errores típicos: {', '.join(p['errores_esperados'])}")
            for valores in elegidas:
                inst = Instancia(p, valores)
                lineas.append(f"- {inst.texto('enunciado')}")
            if "enunciado_planteo" in p:
                lineas.append(f"- Para plantear (con los números de cualquier instancia): "
                              f"{Instancia(p, elegidas[0]).texto('enunciado_planteo')}")
            ej = Instancia(p, elegidas[0]).pistas()
            lineas.append(f"  - Pistas de referencia (para la primera instancia; adaptá los números): "
                          + " · ".join(f"({i}) {ej[k]}" for i, k in enumerate(["P1", "P2", "P3", "P4"], 1)))
            lineas.append("")
    lineas.append(FIN)
    return "\n".join(lineas)


def actualizar_prompt(plantillas):
    texto = PROMPT.read_text(encoding="utf-8")
    if INICIO not in texto or FIN not in texto:
        raise SystemExit(f"{PROMPT} no tiene los marcadores {INICIO} / {FIN}")
    antes, resto = texto.split(INICIO, 1)
    _, despues = resto.split(FIN, 1)
    PROMPT.write_text(antes + catalogo(plantillas) + despues, encoding="utf-8")
    print(f"Catálogo actualizado en {PROMPT.relative_to(AQUI.parent.parent)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--actualizar-prompt", action="store_true", help="reescribir el catálogo del banco en system_prompt.md")
    args = ap.parse_args()

    plantillas = cargar_plantillas()
    v = Verificador()
    ids = Counter(p.get("id") for p in plantillas)
    for pid, n in ids.items():
        v.check(n == 1, f"id repetido: {pid}")
    por_tema = Counter(p.get("tema") for p in plantillas)
    for tema in TEMAS:
        v.check(por_tema[tema] >= 3, f"tema {tema}: {por_tema[tema]} plantillas (mínimo 3)")
    v.check(len(plantillas) >= 18, f"{len(plantillas)} plantillas (mínimo 18)")

    total_inst = 0
    for p in plantillas:
        total_inst += v.plantilla(p)

    print(f"Plantillas: {len(plantillas)} · instancias verificadas: {total_inst} · chequeos: {v.chequeos}")
    print("Por tema: " + ", ".join(f"{t} {por_tema[t]}" for t in TEMAS))
    if v.fallos:
        print(f"\nFALLOS: {len(v.fallos)}")
        for f in v.fallos:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("Fallos: 0")
    if args.actualizar_prompt:
        actualizar_prompt(plantillas)


if __name__ == "__main__":
    main()
