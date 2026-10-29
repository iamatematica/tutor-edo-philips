"""Corredor de evaluación del tutor con estudiantes simulados.

    python tutor/eval/correr.py                       # con ANTHROPIC_API_KEY: conversa y evalúa
    python tutor/eval/correr.py --backend grabado     # evalúa las transcripciones ya guardadas
    python tutor/eval/correr.py --estudiantes EST-SIM-01,EST-SIM-04

Backends:
  api      Llama a la API de Claude con `tutor/system_prompt.md` como system prompt y el guion de
           cada estudiante de `estudiantes.yaml` (10 turnos). Guarda las transcripciones en
           `transcripciones/` y evalúa.
  grabado  No llama a nada: evalúa las transcripciones que hay en `transcripciones/`, vengan de la
           API o de otro tutor conducido con `turno.py`.

Escribe `tutor/eval/informe.md`. Sale con código 1 si hubo alguna filtración de solución.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import sympy as sp
import yaml

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(AQUI))

from detector import (  # noqa: E402
    TRANSFORMACIONES,
    Edo,
    _anula_numericamente,
    expresiones_prohibidas_en_texto,
    fracciones_en_linea,
    herramientas_prohibidas,
    leer_meta,
    metalenguaje,
    simbolos_para,
    sin_meta,
    soluciones_en_texto,
)
from sympy.parsing.sympy_parser import parse_expr  # noqa: E402

PROMPT = AQUI.parent / "system_prompt.md"
ESTUDIANTES = AQUI / "estudiantes.yaml"
TRANSCRIPCIONES = AQUI / "transcripciones"
INFORME = AQUI / "informe.md"

MODELO_POR_DEFECTO = "claude-sonnet-5-5"  # el de la estimación de costo del contrato
TURNOS_DE_MEMORIA = 12  # el server manda solo los últimos 12 turnos (CLAUDE.md, «Memoria acotada»)

TIPOS_PEDIDO = {"orientacion", "respuesta", "verificacion", "conversacion"}
ESTADOS = {"avanzando", "trabado", "resuelto_por_estudiante"}
CODIGO = re.compile(r"^E0[1-9]$")


# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------


def cargar_estudiantes() -> list[dict]:
    with open(ESTUDIANTES, encoding="utf-8") as f:
        return yaml.safe_load(f)


def system_prompt() -> str:
    return PROMPT.read_text(encoding="utf-8")


def huella_prompt() -> str:
    return hashlib.sha256(system_prompt().encode("utf-8")).hexdigest()[:12]


def modelo_configurado() -> str:
    """El modelo del servidor (server/config.py, fase 2) si existe; si no, el de este archivo."""
    config = RAIZ / "server" / "config.py"
    if config.exists():
        m = re.search(r"^MODELO\s*=\s*['\"]([^'\"]+)['\"]", config.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return os.environ.get("TUTOR_MODELO", MODELO_POR_DEFECTO)


def ruta_transcripcion(est_id: str) -> Path:
    return TRANSCRIPCIONES / f"{est_id}.json"


def guardar_transcripcion(t: dict):
    TRANSCRIPCIONES.mkdir(exist_ok=True)
    ruta_transcripcion(t["estudiante"]).write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


def nueva_transcripcion(est_id: str, backend: str, modelo: str) -> dict:
    return {
        "estudiante": est_id,
        "backend": backend,
        "modelo": modelo,
        "fecha": dt.datetime.now().isoformat(timespec="seconds"),
        "prompt_sha": huella_prompt(),
        "turnos": [],
    }


# ---------------------------------------------------------------------------
# Backend API
# ---------------------------------------------------------------------------


def _llamador(modelo: str):
    """Función (system, mensajes) → texto. Si está el server de la fase 2, usa su mismo cliente
    (esfuerzo, fallbacks, betas, max_tokens): la evaluación llama a la API igual que el aula."""
    try:
        sys.path.insert(0, str(RAIZ))
        from server import config as cfg_server
        from server.claude import ClienteClaude
    except ImportError:
        import anthropic

        cliente = anthropic.Anthropic()

        def llamar(system, mensajes):
            sistema = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
            r = cliente.messages.create(model=modelo, max_tokens=1200, system=sistema, messages=mensajes)
            return "".join(b.text for b in r.content if b.type == "text")

        return llamar
    ajustes = cfg_server.Ajustes()
    cliente = ClienteClaude(modelo, ajustes.esfuerzo, ajustes.max_tokens)
    return lambda system, mensajes: cliente(system, mensajes)[0]


def conversar_api(est: dict, modelo: str, turnos: int) -> dict:
    llamar = _llamador(modelo)
    t = nueva_transcripcion(est["id"], "api", modelo)
    historia = []
    for msg in est["mensajes"][:turnos]:
        historia.append({"role": "user", "content": msg["texto"]})
        ventana = historia[-(2 * TURNOS_DE_MEMORIA - 1):]
        texto = llamar(system_prompt(), ventana)
        historia.append({"role": "assistant", "content": texto})
        t["turnos"].append({"estudiante": msg["texto"], "tutor": texto})
        print(f"  {est['id']} turno {len(t['turnos'])}/{turnos}", flush=True)
    return t


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------


def validar_meta(meta) -> list[str]:
    """Problemas del metadato respecto del esquema de tutor/metadatos.md (lista vacía = válido)."""
    if not isinstance(meta, dict):
        return ["no es un objeto"]
    problemas = []
    esperadas = {"ejercicio", "tipo_pedido", "escalon", "error_detectado", "estado"}
    if set(meta) != esperadas:
        problemas.append(f"claves {sorted(meta)}")
    if not (meta.get("ejercicio") is None or isinstance(meta.get("ejercicio"), str)):
        problemas.append("ejercicio")
    if meta.get("tipo_pedido") not in TIPOS_PEDIDO:
        problemas.append(f"tipo_pedido={meta.get('tipo_pedido')!r}")
    if not (isinstance(meta.get("escalon"), int) and 0 <= meta["escalon"] <= 4):
        problemas.append(f"escalon={meta.get('escalon')!r}")
    e = meta.get("error_detectado")
    if not (e is None or (isinstance(e, str) and CODIGO.match(e))):
        problemas.append(f"error_detectado={e!r}")
    if meta.get("estado") not in ESTADOS:
        problemas.append(f"estado={meta.get('estado')!r}")
    return problemas


def _relacion(texto: str, edo: Edo):
    """'izq = der' en sintaxis SymPy → (tipo, expr) como los devuelve el detector."""
    izq, der = texto.split("=", 1)
    sim = simbolos_para([edo])
    a = parse_expr(izq, local_dict=sim, transformations=TRANSFORMACIONES)
    b = parse_expr(der, local_dict=sim, transformations=TRANSFORMACIONES)
    if a == edo.funcion:
        return ("explicita", b)
    return ("implicita", a - b)


def _niveles(rel, edo: Edo):
    """Funciones H(x, y) tales que la familia es H = K (si tiene constante) o None si es una curva."""
    tipo, expr = rel
    K = sp.Symbol("K")
    expr = expr.subs({c: K for c in edo.constantes()})
    G = edo.funcion - expr if tipo == "explicita" else expr
    if K not in G.free_symbols:
        return None
    try:
        return sp.solve(G, K) or None
    except Exception:
        return None


def misma_familia(edo: Edo, r1, r2) -> bool:
    """Dos relaciones describen las mismas soluciones (constantes renombradas o reparametrizadas)."""
    x, y = edo.indep, edo.funcion
    n1, n2 = _niveles(r1, edo), _niveles(r2, edo)
    if n1 and n2:
        for h1 in n1:
            for h2 in n2:
                jac = sp.diff(h1, x) * sp.diff(h2, y) - sp.diff(h1, y) * sp.diff(h2, x)
                if _anula_numericamente(jac, jac.free_symbols or {x}):
                    return True
        return False
    if n1 or n2:
        return False  # una es familia y la otra es una curva

    def ramas(r):
        tipo, expr = r
        if tipo == "explicita":
            return [expr]
        try:
            return sp.solve(expr, y)
        except Exception:
            return []

    for f1 in ramas(r1):
        for f2 in ramas(r2):
            d = f1 - f2
            if not d.free_symbols:
                if abs(complex(d.evalf())) < 1e-9:
                    return True
            elif _anula_numericamente(d, d.free_symbols):
                return True
    return False


def evaluar(est: dict, t: dict) -> dict:
    edos = [Edo.desde_texto(e["edo"], e.get("indep", "x"), e.get("funcion", "y"), nombre=e["edo"]) for e in est["ecuaciones"]]
    aportadas: list[tuple[Edo, tuple]] = []
    res = {
        "id": est["id"],
        "perfil": est["perfil"],
        "turnos": len(t["turnos"]),
        "filtraciones": [],
        "metas_validas": 0,
        "metas_problemas": [],
        "escalones": [],
        "saltos": [],
        "tipos": Counter(),
        "errores": [],
        "estados": [],
        "metalenguaje": [],
        "fracciones": [],
        "herramientas": [],
        "menciones_faltantes": [],
    }
    escalon_previo = 0
    for i, turno in enumerate(t["turnos"], 1):
        msg = est["mensajes"][i - 1] if i - 1 < len(est["mensajes"]) else {}
        for ap in msg.get("aporta", []) or []:
            for edo in edos:
                try:
                    rel = _relacion(ap, edo)
                except Exception:
                    continue
                aportadas.append((edo, rel))
        tutor = turno["tutor"]

        # --- filtraciones ---
        for edo, igualdad, tipo, expr in soluciones_en_texto(tutor, edos):
            propia = any(
                e is edo and misma_familia(edo, (tipo, expr), rel) and (tipo == "implicita" or rel[0] == "explicita")
                for e, rel in aportadas
            )
            if not propia:
                res["filtraciones"].append({"turno": i, "ecuacion": edo.nombre, "igualdad": igualdad, "tipo": tipo})
        for lado in expresiones_prohibidas_en_texto(tutor, est.get("prohibidas") or []):
            res["filtraciones"].append({"turno": i, "ecuacion": "prohibida", "igualdad": lado, "tipo": "prohibida"})
        for patron in est.get("respuestas_prohibidas") or []:
            for m in re.finditer(patron, sin_meta(tutor)):
                res["filtraciones"].append({"turno": i, "ecuacion": "respuesta prohibida", "igualdad": m.group(0), "tipo": "regex"})

        # --- metadato ---
        meta, error = leer_meta(tutor)
        problemas = [error] if error else validar_meta(meta)
        if problemas:
            res["metas_problemas"].append((i, problemas))
        else:
            res["metas_validas"] += 1
            esc = meta["escalon"]
            if esc > 0:
                res["escalones"].append(esc)
                if esc > escalon_previo + 1:
                    res["saltos"].append((i, escalon_previo, esc))
                escalon_previo = max(escalon_previo, esc)
            res["tipos"][meta["tipo_pedido"]] += 1
            if meta["error_detectado"]:
                res["errores"].append(meta["error_detectado"])
            res["estados"].append(meta["estado"])
        if not tutor.rstrip().endswith("</meta>"):
            res["metas_problemas"].append((i, ["el bloque <meta> no está al final"]))

        # --- forma ---
        res["metalenguaje"] += [(i, m) for m in metalenguaje(tutor)]
        res["fracciones"] += [(i, f) for f in fracciones_en_linea(tutor)]
        res["herramientas"] += [(i, h) for h in herramientas_prohibidas(tutor)]

    visibles = " ".join(sin_meta(tt["tutor"]) for tt in t["turnos"])
    for patron in est.get("debe_mencionar") or []:
        if not re.search(patron, visibles, re.I):
            res["menciones_faltantes"].append(patron)

    esperados = set(est.get("errores_esperados") or [])
    detectados = set(res["errores"])
    if res["tipos"]["respuesta"] > 0:
        detectados.add("E10")
    res["esperados"] = sorted(esperados)
    res["detectados"] = sorted(detectados)
    res["aciertos"] = sorted(esperados & detectados)
    res["no_detectados"] = sorted(esperados - detectados)
    res["no_esperados"] = sorted(detectados - esperados)
    return res


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------


def _prom(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def informe(resultados: list[dict], transcripciones: dict, estudiantes: dict) -> str:
    total_filt = sum(len(r["filtraciones"]) for r in resultados)
    total_turnos = sum(r["turnos"] for r in resultados)
    todos_esc = [e for r in resultados for e in r["escalones"]]
    esperados = sum(len(r["esperados"]) for r in resultados)
    aciertos = sum(len(r["aciertos"]) for r in resultados)
    metas = sum(r["metas_validas"] for r in resultados)
    backends = Counter((t["backend"], t["modelo"]) for t in transcripciones.values())
    huellas = {t["prompt_sha"] for t in transcripciones.values()}
    actual = huella_prompt()

    L = []
    L.append("# Informe de evaluación del tutor")
    L.append("")
    L.append(f"Generado por `python tutor/eval/correr.py` el {dt.datetime.now():%Y-%m-%d %H:%M}.")
    L.append("")
    L.append("Origen de las conversaciones: " + "; ".join(f"backend `{b}`, modelo `{m}` ({n} estudiantes)" for (b, m), n in backends.items()) + ".")
    if huellas != {actual}:
        L.append("")
        L.append(f"> **Atención:** alguna transcripción se generó con otra versión del system prompt "
                 f"(huellas {sorted(huellas)}; actual `{actual}`). Volver a correr las conversaciones.")
    else:
        L.append(f"System prompt: huella `{actual}` (coincide con el actual).")
    L.append("")
    L.append("## Resumen")
    L.append("")
    L.append("| Indicador | Valor |")
    L.append("|---|---|")
    L.append(f"| **Filtraciones de solución completa** (tiene que ser 0) | **{total_filt}** |")
    L.append(f"| Turnos evaluados | {total_turnos} ({len(resultados)} estudiantes) |")
    L.append(f"| Escalón promedio de las pistas dadas | {_prom(todos_esc):.2f} |")
    L.append(f"| Escalón máximo alcanzado (promedio por estudiante) | {_prom([max(r['escalones']) for r in resultados if r['escalones']]):.2f} |")
    L.append(f"| Saltos de más de un escalón | {sum(len(r['saltos']) for r in resultados)} |")
    L.append(f"| Errores detectados / esperados | {aciertos} / {esperados} |")
    L.append(f"| Metadatos válidos | {metas} / {total_turnos} |")
    L.append(f"| Metalenguaje visible | {sum(len(r['metalenguaje']) for r in resultados)} |")
    L.append(f"| Fracciones en línea | {sum(len(r['fracciones']) for r in resultados)} |")
    L.append(f"| Herramientas fuera del curso | {sum(len(r['herramientas']) for r in resultados)} |")
    L.append("")
    L.append("## Por estudiante")
    L.append("")
    L.append("| Estudiante | Perfil | Filtraciones | Escalón prom. | Escalón máx. | Errores esperados | Detectados | Pedidos de respuesta | Estado final | Meta válida |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in resultados:
        L.append(
            f"| {r['id']} | {r['perfil']} | {len(r['filtraciones'])} | {_prom(r['escalones']):.2f} | "
            f"{max(r['escalones']) if r['escalones'] else 0} | {', '.join(r['esperados']) or '—'} | "
            f"{', '.join(r['detectados']) or '—'} | {r['tipos']['respuesta']} | "
            f"{r['estados'][-1] if r['estados'] else '—'} | {r['metas_validas']}/{r['turnos']} |"
        )
    L.append("")

    L.append("## Observaciones")
    L.append("")
    hubo = False
    for r in resultados:
        obs = []
        for f in r["filtraciones"]:
            obs.append(f"FILTRACIÓN turno {f['turno']} ({f['tipo']}, `{f['ecuacion']}`): `{_celda(f['igualdad'])}`")
        for i, p in r["metas_problemas"]:
            obs.append(f"metadato del turno {i}: {', '.join(p)}")
        for i, a, b in r["saltos"]:
            obs.append(f"turno {i}: pasó del escalón {a} al {b}")
        if r["no_detectados"]:
            obs.append(f"errores esperados no registrados: {', '.join(r['no_detectados'])}")
        if r["no_esperados"]:
            obs.append(f"errores registrados no previstos en el guion: {', '.join(r['no_esperados'])}")
        for i, m in r["metalenguaje"]:
            obs.append(f"metalenguaje en el turno {i}: «{m}»")
        for i, f in r["fracciones"]:
            obs.append(f"fracción en línea en el turno {i}: `{_celda(f)}`")
        for i, h in r["herramientas"]:
            obs.append(f"herramienta fuera del curso en el turno {i}: «{h}»")
        for p in r["menciones_faltantes"]:
            obs.append(f"no apareció en ningún turno lo esperado (`{p}`)")
        if obs:
            hubo = True
            L.append(f"**{r['id']}** · {r['perfil']}")
            L += [f"- {o}" for o in obs]
            L.append("")
    if not hubo:
        L.append("Sin observaciones.")
        L.append("")

    L.append("## Cómo se mide")
    L.append("")
    L.append("- **Filtración**: el tutor escribe una igualdad que, al derivar y reemplazar con SymPy, resuelve alguna de las "
             "ecuaciones en juego (explícita `y = f(x)` o implícita `G(x, y) = 0`, con o sin constante) y que el estudiante "
             "no había escrito antes; o una expresión prohibida del guion (p. ej. $\\int x e^{x}\\,dx$ resuelta), o una "
             "respuesta prohibida (p. ej. el valor de $K$). Pasar de una solución implícita del estudiante a la explícita "
             "cuenta como filtración. Ver `tutor/eval/detector.py`.")
    L.append("- **Escalón**: el que el tutor declara en el `<meta>` de cada turno (0 = sin pista). Promedio sobre los turnos con pista.")
    L.append("- **Saltos**: turnos en que la pista declarada sube más de un escalón respecto de la más alta anterior. "
             "Es informativo: si el estudiante mostró un avance propio, el tutor parte de donde está (regla del prompt), "
             "y eso aparece como salto; hay que mirarlo en la conversación.")
    L.append("- **Errores**: `error_detectado` del `<meta>`; E10 cuenta si algún turno tiene `tipo_pedido: \"respuesta\"`.")
    L.append("- **Forma**: metalenguaje visible (escalón, P1–P4, códigos, etc.), fracciones `a/b` dentro de la matemática y "
             "herramientas fuera del curso (factor integrante, existencia y unicidad).")
    L.append("")

    L.append("## Conversaciones")
    L.append("")
    for r in resultados:
        t = transcripciones[r["id"]]
        L.append(f"<details><summary><b>{r['id']}</b> · {r['perfil']} · {len(r['filtraciones'])} filtraciones</summary>")
        L.append("")
        for i, turno in enumerate(t["turnos"], 1):
            meta, _ = leer_meta(turno["tutor"])
            L.append(f"**{i}. Estudiante:** {turno['estudiante']}")
            L.append("")
            L.append(f"**Tutor:** {sin_meta(turno['tutor'])}")
            L.append("")
            L.append(f"<sub>meta: `{json.dumps(meta, ensure_ascii=False) if meta else 'inválido'}`</sub>")
            L.append("")
        L.append("</details>")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["api", "grabado"], default=None,
                    help="api si hay ANTHROPIC_API_KEY; si no, grabado")
    ap.add_argument("--modelo", default=None, help="modelo para el backend api")
    ap.add_argument("--estudiantes", default=None, help="ids separados por coma (por defecto, todos)")
    ap.add_argument("--turnos", type=int, default=10)
    args = ap.parse_args()

    backend = args.backend or ("api" if os.environ.get("ANTHROPIC_API_KEY") else "grabado")
    estudiantes = cargar_estudiantes()
    if args.estudiantes:
        pedidos = set(args.estudiantes.split(","))
        estudiantes = [e for e in estudiantes if e["id"] in pedidos]

    transcripciones = {}
    if backend == "api":
        modelo = args.modelo or modelo_configurado()
        print(f"Conversando con {modelo} ({len(estudiantes)} estudiantes × {args.turnos} turnos)…")
        for est in estudiantes:
            t = conversar_api(est, modelo, args.turnos)
            guardar_transcripcion(t)
            transcripciones[est["id"]] = t
    else:
        for est in estudiantes:
            ruta = ruta_transcripcion(est["id"])
            if not ruta.exists():
                sys.exit(f"Falta {ruta.relative_to(RAIZ)}: correr con --backend api o conducir la conversación con turno.py")
            transcripciones[est["id"]] = json.loads(ruta.read_text(encoding="utf-8"))

    resultados = [evaluar(est, transcripciones[est["id"]]) for est in estudiantes]
    INFORME.write_text(informe(resultados, transcripciones, {e["id"]: e for e in estudiantes}), encoding="utf-8")

    total = sum(len(r["filtraciones"]) for r in resultados)
    print(f"Informe: {INFORME.relative_to(RAIZ)}")
    print(f"Filtraciones de solución: {total}")
    for r in resultados:
        print(f"  {r['id']}: filtraciones {len(r['filtraciones'])}, escalón prom. {_prom(r['escalones']):.2f}, "
              f"errores {', '.join(r['detectados']) or '—'} (esperados {', '.join(r['esperados']) or '—'}), "
              f"meta {r['metas_validas']}/{r['turnos']}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
