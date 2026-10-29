"""Métricas del panel docente, calculadas a partir de la base y del <meta> de cada turno.

Definiciones (las mismas que muestra el panel y que van en los CSV):
- ingreso: una fila de `sesiones` (se abre en el login, o al volver tras 20 minutos sin mensajes).
- semana: de lunes a domingo, en hora de Buenos Aires, según el inicio de la sesión.
- minutos conectados: suma de (ultima_actividad − inicio) de las sesiones.
- turno: un mensaje del estudiante respondido por el tutor.
- turnos por sesión: turnos / sesiones con al menos un turno (un login sin mensajes no cuenta).
- ejercicio abordado: id del banco que aparece en algún <meta> del estudiante.
- ejercicio resuelto: abordado con algún <meta> en estado `resuelto_por_estudiante`.
- escalón promedio alcanzado: promedio, sobre los pares (estudiante, ejercicio), del escalón
  máximo que se le dio en ese ejercicio.
- errores: `error_detectado` de cada <meta>; E10 se cuenta como los turnos con `tipo_pedido: respuesta`.
- costo estimado: turnos del día / del mes (hora de Buenos Aires) × costo medio por turno.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import config
from .db import BaseDatos, iso

TIPOS_PEDIDO = ("orientacion", "respuesta", "verificacion", "conversacion")
DISPOSITIVOS = ("celular", "computadora")
CODIGOS = tuple(f"E{n:02d}" for n in range(1, 11))
TEXTO_PISTA = "Pista"


def _fecha(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def _meta(fila) -> dict | None:
    if not fila["meta_json"]:
        return None
    try:
        meta = json.loads(fila["meta_json"])
    except ValueError:
        return None
    return meta if isinstance(meta, dict) else None


def _lunes(cuando: datetime, zona: ZoneInfo) -> date:
    local = cuando.astimezone(zona).date()
    return local - timedelta(days=local.weekday())


def _redondear(x: float | None, cifras: int = 2) -> float | None:
    return None if x is None else round(x, cifras)


def _proporcion(a: int, total: int) -> float | None:
    return round(a / total, 3) if total else None


def hora_local(texto: str, zona: ZoneInfo) -> str:
    """'2026-11-03T18:00:00+00:00' → '2026-11-03 15:00' (Buenos Aires)."""
    return _fecha(texto).astimezone(zona).strftime("%Y-%m-%d %H:%M")


def _leer(bd: BaseDatos):
    with bd.conexion() as c:
        estudiantes = [f["id"] for f in c.execute("SELECT id FROM estudiantes ORDER BY id")]
        sesiones = c.execute("SELECT * FROM sesiones ORDER BY id").fetchall()
        mensajes = c.execute("SELECT * FROM mensajes ORDER BY id").fetchall()
    return estudiantes, sesiones, mensajes


class _Acumulado:
    """Contadores de un estudiante (o del curso entero)."""

    def __init__(self):
        self.ingresos = 0
        self.ingresos_semana: Counter[date] = Counter()
        self.minutos = 0.0
        self.sesiones_con_turnos = 0
        self.turnos = 0
        self.dispositivos: Counter[str] = Counter()
        self.pedidos: Counter[str] = Counter()
        self.errores: Counter[str] = Counter()
        # ejercicio → escalón máximo, y ejercicios resueltos
        self.escalon_max: dict[str, int] = {}
        self.resueltos: set[str] = set()
        self.ultima_actividad: str | None = None


def calcular(bd: BaseDatos, cuando: datetime, costo_turno: float = config.COSTO_MEDIO_TURNO_USD,
             tope_mensual: float = config.TOPE_MENSUAL_USD, zona_horaria: str = config.ZONA_HORARIA) -> dict:
    zona = ZoneInfo(zona_horaria)
    estudiantes, sesiones, mensajes = _leer(bd)

    por_est: dict[str, _Acumulado] = defaultdict(_Acumulado)
    for est in estudiantes:
        por_est[est]  # aparecen todos, aunque nunca hayan entrado

    turnos_sesion: Counter[int] = Counter()
    for m in mensajes:
        if m["rol"] == "user":
            turnos_sesion[m["sesion"]] += 1

    semanas: set[date] = set()
    for s in sesiones:
        a = por_est[s["estudiante"]]
        a.ingresos += 1
        lunes = _lunes(_fecha(s["inicio"]), zona)
        semanas.add(lunes)
        a.ingresos_semana[lunes] += 1
        a.minutos += max(0.0, (_fecha(s["ultima_actividad"]) - _fecha(s["inicio"])).total_seconds() / 60)
        a.dispositivos[s["dispositivo"]] += 1
        if turnos_sesion[s["id"]]:
            a.sesiones_con_turnos += 1
        if a.ultima_actividad is None or s["ultima_actividad"] > a.ultima_actividad:
            a.ultima_actividad = s["ultima_actividad"]

    # Por ejercicio: quiénes lo abordaron, quiénes se trabaron, quiénes lo resolvieron.
    ej_abordado: dict[str, set[str]] = defaultdict(set)
    ej_trabado: dict[str, set[str]] = defaultdict(set)
    ej_turnos_trabado: Counter[str] = Counter()
    ej_resuelto: dict[str, set[str]] = defaultdict(set)
    ej_turnos: Counter[str] = Counter()
    metas_validos = 0
    respuestas_tutor = 0

    for m in mensajes:
        a = por_est[m["estudiante"]]
        if m["rol"] == "user":
            a.turnos += 1
            continue
        respuestas_tutor += 1
        meta = _meta(m)
        if meta is None:
            continue
        metas_validos += 1
        tipo = meta.get("tipo_pedido")
        if tipo in TIPOS_PEDIDO:
            a.pedidos[tipo] += 1
            if tipo == "respuesta":
                a.errores["E10"] += 1
        if meta.get("error_detectado") in CODIGOS:
            a.errores[meta["error_detectado"]] += 1
        ej = meta.get("ejercicio")
        if not ej:
            continue
        ej = str(ej).upper()
        escalon = meta.get("escalon") if isinstance(meta.get("escalon"), int) else 0
        a.escalon_max[ej] = max(a.escalon_max.get(ej, 0), escalon)
        ej_abordado[ej].add(m["estudiante"])
        ej_turnos[ej] += 1
        if meta.get("estado") == "trabado":
            ej_trabado[ej].add(m["estudiante"])
            ej_turnos_trabado[ej] += 1
        if meta.get("estado") == "resuelto_por_estudiante":
            a.resueltos.add(ej)
            ej_resuelto[ej].add(m["estudiante"])

    lista_semanas = sorted(semanas)

    def resumen(a: _Acumulado) -> dict:
        pedidos_total = sum(a.pedidos.values())
        orient, resp = a.pedidos["orientacion"], a.pedidos["respuesta"]
        escalones = list(a.escalon_max.values())
        return {
            "ingresos": a.ingresos,
            "ingresos_por_semana": [a.ingresos_semana[s] for s in lista_semanas],
            "minutos": _redondear(a.minutos, 1),
            "turnos": a.turnos,
            "turnos_por_sesion": _redondear(a.turnos / a.sesiones_con_turnos if a.sesiones_con_turnos else None, 1),
            "dispositivos": {d: a.dispositivos[d] for d in DISPOSITIVOS},
            "ejercicios_abordados": len(a.escalon_max),
            "ejercicios_resueltos": len(a.resueltos),
            "pedidos": {t: a.pedidos[t] for t in TIPOS_PEDIDO},
            "proporcion_orientacion": _proporcion(orient, orient + resp),
            "proporcion_respuesta": _proporcion(resp, pedidos_total),
            "errores": {c: a.errores[c] for c in CODIGOS if a.errores[c]},
            "escalon_promedio": _redondear(sum(escalones) / len(escalones) if escalones else None),
            "ultima_actividad": hora_local(a.ultima_actividad, zona) if a.ultima_actividad else None,
        }

    filas_est = []
    curso = _Acumulado()
    pares_escalon: list[int] = []
    for est in sorted(por_est):
        a = por_est[est]
        fila = resumen(a)
        fila["id"] = est
        fila["lista_abordados"] = sorted(a.escalon_max)
        fila["lista_resueltos"] = sorted(a.resueltos)
        filas_est.append(fila)
        # El curso suma a todos.
        curso.ingresos += a.ingresos
        curso.ingresos_semana.update(a.ingresos_semana)
        curso.minutos += a.minutos
        curso.sesiones_con_turnos += a.sesiones_con_turnos
        curso.turnos += a.turnos
        curso.dispositivos.update(a.dispositivos)
        curso.pedidos.update(a.pedidos)
        curso.errores.update(a.errores)
        pares_escalon.extend(a.escalon_max.values())

    resumen_curso = resumen(curso)
    resumen_curso.pop("ultima_actividad")
    resumen_curso["estudiantes"] = len(estudiantes)
    resumen_curso["estudiantes_activos"] = sum(1 for f in filas_est if f["turnos"])
    resumen_curso["ejercicios_abordados"] = len(ej_abordado)
    resumen_curso["ejercicios_resueltos"] = len(ej_resuelto)
    resumen_curso["resoluciones"] = sum(len(v) for v in ej_resuelto.values())
    resumen_curso["escalon_promedio"] = _redondear(
        sum(pares_escalon) / len(pares_escalon) if pares_escalon else None
    )
    resumen_curso["metas_validos"] = metas_validos
    resumen_curso["respuestas_tutor"] = respuestas_tutor

    ejercicios = [
        {
            "ejercicio": ej,
            "abordado_por": len(ej_abordado[ej]),
            "trabados": len(ej_trabado[ej]),
            "turnos_trabado": ej_turnos_trabado[ej],
            "resuelto_por": len(ej_resuelto[ej]),
            "turnos": ej_turnos[ej],
            "escalon_promedio": _redondear(
                sum(por_est[e].escalon_max[ej] for e in ej_abordado[ej]) / len(ej_abordado[ej])
            ),
        }
        for ej in ej_abordado
    ]
    # Más trabados primero: estudiantes que se trabaron, después turnos trabados.
    ejercicios.sort(key=lambda e: (-e["trabados"], -e["turnos_trabado"], -e["abordado_por"], e["ejercicio"]))

    errores = [
        {"codigo": c, "veces": curso.errores[c],
         "estudiantes": sum(1 for est in por_est.values() if est.errores[c])}
        for c in CODIGOS if curso.errores[c]
    ]
    errores.sort(key=lambda e: (-e["veces"], e["codigo"]))

    # Costo: turnos del día y del mes en hora de Buenos Aires.
    local = cuando.astimezone(zona)
    inicio_dia = local.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = inicio_dia.replace(day=1)
    desde_dia, desde_mes = iso(inicio_dia), iso(inicio_mes)
    turnos_dia = sum(1 for m in mensajes if m["rol"] == "user" and m["creado"] >= desde_dia)
    turnos_mes = sum(1 for m in mensajes if m["rol"] == "user" and m["creado"] >= desde_mes)
    costo_mes = turnos_mes * costo_turno

    return {
        "generado": local.strftime("%Y-%m-%d %H:%M"),
        "semanas": [s.isoformat() for s in lista_semanas],
        "curso": resumen_curso,
        "estudiantes": filas_est,
        "ejercicios": ejercicios,
        "errores": errores,
        "costo": {
            "costo_medio_turno_usd": costo_turno,
            "turnos_dia": turnos_dia,
            "turnos_mes": turnos_mes,
            "costo_dia_usd": round(turnos_dia * costo_turno, 2),
            "costo_mes_usd": round(costo_mes, 2),
            "tope_mensual_usd": tope_mensual,
            "proporcion_tope": round(costo_mes / tope_mensual, 3) if tope_mensual else None,
        },
    }


def conversacion(bd: BaseDatos, est_id: str, zona_horaria: str = config.ZONA_HORARIA) -> dict:
    """Todas las sesiones del estudiante con sus mensajes y el <meta> de cada respuesta."""
    zona = ZoneInfo(zona_horaria)
    with bd.conexion() as c:
        sesiones = c.execute("SELECT * FROM sesiones WHERE estudiante = ? ORDER BY id", (est_id,)).fetchall()
        mensajes = c.execute("SELECT * FROM mensajes WHERE estudiante = ? ORDER BY id", (est_id,)).fetchall()
    por_sesion: dict[int, list] = defaultdict(list)
    for m in mensajes:
        por_sesion[m["sesion"]].append({
            "id": m["id"],
            "rol": m["rol"],
            "texto": m["texto"],
            "pista": m["rol"] == "user" and m["texto"] == TEXTO_PISTA,
            "meta": _meta(m) if m["rol"] == "assistant" else None,
            "creado": hora_local(m["creado"], zona),
        })
    return {
        "id": est_id,
        "sesiones": [
            {
                "id": s["id"],
                "inicio": hora_local(s["inicio"], zona),
                "ultima_actividad": hora_local(s["ultima_actividad"], zona),
                "minutos": round(max(0.0, (_fecha(s["ultima_actividad"]) - _fecha(s["inicio"])).total_seconds() / 60), 1),
                "dispositivo": s["dispositivo"],
                "turnos": sum(1 for m in por_sesion[s["id"]] if m["rol"] == "user"),
                "mensajes": por_sesion[s["id"]],
            }
            for s in sesiones
        ],
    }


# ---------- tablas para exportar a CSV ----------

def _num(x) -> str:
    """Números con coma decimal, para que Excel en castellano los lea como números."""
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:g}".replace(".", ",")
    texto = str(x)
    # Un texto que empieza con = + - @ Excel lo toma como fórmula: se neutraliza con un apóstrofo.
    if isinstance(x, str) and texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + texto
    return texto


def tablas_csv(bd: BaseDatos, cuando: datetime, **kw) -> dict[str, tuple[list[str], list[list]]]:
    """Cada tabla del panel como (encabezados, filas), lista para csv.writer."""
    m = calcular(bd, cuando, **kw)
    zona = ZoneInfo(kw.get("zona_horaria", config.ZONA_HORARIA))
    semanas = m["semanas"]

    def fila_est(f: dict, ident: str) -> list:
        return [
            ident, f["ingresos"], f["minutos"], f["turnos"], f["turnos_por_sesion"],
            f["dispositivos"]["celular"], f["dispositivos"]["computadora"],
            f["ejercicios_abordados"], f["ejercicios_resueltos"],
            *(f["pedidos"][t] for t in TIPOS_PEDIDO),
            f["proporcion_orientacion"], f["escalon_promedio"],
            *(f["errores"].get(c, 0) for c in CODIGOS),
        ]

    enc_est = [
        "estudiante", "ingresos", "minutos_conectados", "turnos", "turnos_por_sesion",
        "sesiones_celular", "sesiones_computadora", "ejercicios_abordados", "ejercicios_resueltos",
        *(f"pedidos_{t}" for t in TIPOS_PEDIDO), "proporcion_orientacion", "escalon_promedio", *CODIGOS,
    ]
    estudiantes = (
        enc_est + ["abordados", "resueltos", "ultima_actividad"],
        [fila_est(f, f["id"]) + [" ".join(f["lista_abordados"]), " ".join(f["lista_resueltos"]),
                                 f["ultima_actividad"] or ""] for f in m["estudiantes"]],
    )
    curso = (enc_est, [fila_est(m["curso"], "CURSO")])

    ingresos_semana = (
        ["estudiante", *(f"semana_{s}" for s in semanas), "total"],
        [[f["id"], *f["ingresos_por_semana"], f["ingresos"]] for f in m["estudiantes"]]
        + [["CURSO", *m["curso"]["ingresos_por_semana"], m["curso"]["ingresos"]]],
    )
    ejercicios = (
        ["ejercicio", "abordado_por", "trabados", "turnos_trabado", "resuelto_por", "turnos", "escalon_promedio"],
        [[e["ejercicio"], e["abordado_por"], e["trabados"], e["turnos_trabado"], e["resuelto_por"], e["turnos"],
          e["escalon_promedio"]] for e in m["ejercicios"]],
    )
    errores = (["codigo", "veces", "estudiantes"], [[e["codigo"], e["veces"], e["estudiantes"]] for e in m["errores"]])
    c = m["costo"]
    costo = (
        ["generado", "turnos_dia", "turnos_mes", "costo_medio_turno_usd", "costo_dia_usd", "costo_mes_usd",
         "tope_mensual_usd"],
        [[m["generado"], c["turnos_dia"], c["turnos_mes"], c["costo_medio_turno_usd"], c["costo_dia_usd"],
          c["costo_mes_usd"], c["tope_mensual_usd"]]],
    )

    with bd.conexion() as con:
        filas_ses = con.execute("SELECT * FROM sesiones ORDER BY id").fetchall()
        filas_msj = con.execute("SELECT * FROM mensajes ORDER BY id").fetchall()
    turnos_sesion: Counter[int] = Counter(f["sesion"] for f in filas_msj if f["rol"] == "user")
    sesiones = (
        ["sesion", "estudiante", "inicio", "ultima_actividad", "minutos", "dispositivo", "turnos"],
        [[s["id"], s["estudiante"], hora_local(s["inicio"], zona), hora_local(s["ultima_actividad"], zona),
          round(max(0.0, (_fecha(s["ultima_actividad"]) - _fecha(s["inicio"])).total_seconds() / 60), 1),
          s["dispositivo"], turnos_sesion[s["id"]]] for s in filas_ses],
    )
    filas = []
    for f in filas_msj:
        meta = _meta(f) or {}
        filas.append([
            f["id"], f["sesion"], f["estudiante"], hora_local(f["creado"], zona),
            "estudiante" if f["rol"] == "user" else "tutor", f["texto"],
            meta.get("ejercicio") or "", meta.get("tipo_pedido") or "",
            "" if meta.get("escalon") is None else meta["escalon"],
            meta.get("error_detectado") or "", meta.get("estado") or "",
        ])
    mensajes = (
        ["mensaje", "sesion", "estudiante", "creado", "rol", "texto", "ejercicio", "tipo_pedido", "escalon",
         "error_detectado", "estado"],
        filas,
    )

    tablas = {
        "estudiantes": estudiantes, "curso": curso, "semanas": ingresos_semana, "ejercicios": ejercicios,
        "errores": errores, "costo": costo, "sesiones": sesiones, "mensajes": mensajes,
    }
    return {k: (enc, [[_num(x) for x in fila] for fila in filas_t]) for k, (enc, filas_t) in tablas.items()}
