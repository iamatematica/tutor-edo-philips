import csv
import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from server import acceso, config, metricas
from server.app import crear_app
from server.tests.conftest import UA_CELULAR, UA_PC

CLAVE = "clave-docente-de-prueba"
DOC = {"X-Docente-Key": CLAVE}


def meta(ejercicio="SEP-01", tipo="orientacion", escalon=1, error=None, estado="avanzando"):
    return json.dumps({"ejercicio": ejercicio, "tipo_pedido": tipo, "escalon": escalon,
                       "error_detectado": error, "estado": estado})


@pytest.fixture
def ajustes_doc(ajustes):
    ajustes.docente_key = CLAVE
    return ajustes


@pytest.fixture
def app_doc(ajustes_doc, tutor, reloj):
    app = crear_app(ajustes_doc, responder=tutor)
    app.state.reloj = reloj
    for i in range(1, 4):
        app.state.bd.guardar_estudiante(acceso.id_estudiante(i), acceso.hash_codigo(f"COD{i}AA"))
    return app


@pytest.fixture
def doc(app_doc):
    return TestClient(app_doc)


T0 = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)  # martes 3/11, 15:00 en Buenos Aires


def poblar(bd):
    """Datos controlados.

    EST-01: dos sesiones en la semana del 2/11 (celular) y una en la del 9/11 (computadora).
      SEP-01: pista 1, 2 (trabado), 3, resuelto. LIN-01: pide la respuesta, E05.
    EST-02: una sesión, celular, SEP-01 trabado con E02 y pista 4.
    EST-03: nunca entró.
    """
    s1 = bd.abrir_sesion("EST-01", "celular", T0)
    bd.guardar_turno(s1, "EST-01", "y' = 2xy", "¿Qué tipo es?", meta(escalon=1), T0 + timedelta(minutes=2))
    bd.guardar_turno(s1, "EST-01", "Pista", "Separá.", meta(escalon=2, estado="trabado"), T0 + timedelta(minutes=5))
    bd.guardar_turno(s1, "EST-01", "Pista", "Primer paso.", meta(escalon=3), T0 + timedelta(minutes=10))
    s2 = bd.abrir_sesion("EST-01", "celular", T0 + timedelta(days=1))
    bd.guardar_turno(s2, "EST-01", "$y = Ke^{x^2}$", "Verificado.",
                     meta(tipo="verificacion", escalon=0, estado="resuelto_por_estudiante"),
                     T0 + timedelta(days=1, minutes=30))
    s3 = bd.abrir_sesion("EST-01", "computadora", T0 + timedelta(days=7))
    bd.guardar_turno(s3, "EST-01", "Pasame la respuesta", "Probá vos.",
                     meta(ejercicio="lin-01", tipo="respuesta", escalon=1, error="E05"), T0 + timedelta(days=7, minutes=4))
    bd.guardar_turno(s3, "EST-01", "hola", "Hola, volvamos al ejercicio.", None, T0 + timedelta(days=7, minutes=6))

    s4 = bd.abrir_sesion("EST-02", "celular", T0 + timedelta(hours=1))
    bd.guardar_turno(s4, "EST-02", "e^{x^2} + C", "¿Dónde va la C?",
                     meta(escalon=2, error="E02", estado="trabado"), T0 + timedelta(hours=1, minutes=3))
    bd.guardar_turno(s4, "EST-02", "Pista", "Planteo.", meta(escalon=4, estado="trabado"),
                     T0 + timedelta(hours=1, minutes=8))
    # Un login sin mensajes: suma un ingreso pero no cuenta para turnos por sesión.
    bd.abrir_sesion("EST-02", "computadora", T0 + timedelta(days=8))


# ---------- protección ----------

def test_sin_docente_key_el_panel_esta_deshabilitado(cliente):
    r = cliente.get("/api/metricas", headers=DOC)
    assert r.status_code == 503 and "DOCENTE_KEY" in r.json()["detail"]


@pytest.mark.parametrize("ruta", ["/api/metricas", "/api/metricas/conversacion/EST-01", "/api/metricas/csv/estudiantes"])
def test_rutas_piden_la_clave(doc, ruta):
    assert doc.get(ruta).status_code == 401
    assert doc.get(ruta, headers={"X-Docente-Key": "otra"}).status_code == 401
    assert doc.get(ruta, headers=DOC).status_code == 200
    assert doc.get(ruta, headers={"Authorization": f"Bearer {CLAVE}"}).status_code == 200


def test_token_de_estudiante_no_abre_el_panel(doc):
    tok = doc.post("/api/login", json={"id": "EST-01", "codigo": "COD1AA"}).json()["token"]
    assert doc.get("/api/metricas", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_bloqueo_tras_muchos_fallos(doc):
    for _ in range(10):
        assert doc.get("/api/metricas", headers={"X-Docente-Key": "mal"}).status_code == 401
    assert doc.get("/api/metricas", headers=DOC).status_code == 429


def test_html_del_panel_se_sirve_y_no_trae_datos(doc, app_doc):
    poblar(app_doc.state.bd)
    r = doc.get("/panel", follow_redirects=False)
    assert r.status_code in (301, 302, 307, 308) and r.headers["location"] == "/panel/"
    r = doc.get("/panel/")
    assert r.status_code == 200
    assert "Panel docente" in r.text and "Escuela Philips" in r.text and "Matemática · 5.º año" in r.text
    assert "EST-01" not in r.text
    assert r.text.count("Prof. Ariel L. Cardozo Delgado") == 2
    assert doc.get("/panel/panel.js").status_code == 200
    assert doc.get("/panel/panel.css").status_code == 200
    # El panel reusa la hoja de estilos del chat (mismo tema).
    assert "../estilos.css" in r.text and doc.get("/estilos.css").status_code == 200
    # El chat de los estudiantes sigue en /.
    assert "Entrá al tutor" in doc.get("/").text


# ---------- métricas ----------

@pytest.fixture
def m(doc, app_doc, reloj):
    poblar(app_doc.state.bd)
    reloj.t = T0 + timedelta(days=8, hours=2)  # miércoles 11/11
    r = doc.get("/api/metricas", headers=DOC)
    assert r.status_code == 200
    return r.json()


def por_id(m, est):
    return next(f for f in m["estudiantes"] if f["id"] == est)


def test_ingresos_por_semana(m):
    assert m["semanas"] == ["2026-11-02", "2026-11-09"]
    assert por_id(m, "EST-01")["ingresos_por_semana"] == [2, 1]
    assert por_id(m, "EST-02")["ingresos_por_semana"] == [1, 1]
    assert por_id(m, "EST-03")["ingresos_por_semana"] == [0, 0]
    assert m["curso"]["ingresos_por_semana"] == [3, 2]
    assert m["curso"]["ingresos"] == 5


def test_aparecen_todos_los_estudiantes(m):
    assert [f["id"] for f in m["estudiantes"]] == ["EST-01", "EST-02", "EST-03"]
    e3 = por_id(m, "EST-03")
    assert e3["ingresos"] == 0 and e3["turnos"] == 0 and e3["turnos_por_sesion"] is None
    assert e3["escalon_promedio"] is None and e3["ultima_actividad"] is None
    assert m["curso"]["estudiantes"] == 3 and m["curso"]["estudiantes_activos"] == 2


def test_minutos_y_turnos_por_sesion(m):
    e1 = por_id(m, "EST-01")
    assert e1["minutos"] == 10 + 30 + 6
    assert e1["turnos"] == 6 and e1["turnos_por_sesion"] == 2.0
    e2 = por_id(m, "EST-02")
    # El login sin mensajes suma un ingreso, 0 minutos, y no baja el promedio de turnos por sesión.
    assert e2["minutos"] == 8 and e2["turnos"] == 2 and e2["turnos_por_sesion"] == 2.0
    assert m["curso"]["minutos"] == 54 and m["curso"]["turnos"] == 8
    assert m["curso"]["turnos_por_sesion"] == 2.0
    assert e1["ultima_actividad"] == "2026-11-10 15:06"


def test_dispositivo(m):
    assert por_id(m, "EST-01")["dispositivos"] == {"celular": 2, "computadora": 1}
    assert m["curso"]["dispositivos"] == {"celular": 3, "computadora": 2}


def test_ejercicios_abordados_y_resueltos(m):
    e1 = por_id(m, "EST-01")
    assert e1["lista_abordados"] == ["LIN-01", "SEP-01"] and e1["ejercicios_abordados"] == 2
    assert e1["lista_resueltos"] == ["SEP-01"] and e1["ejercicios_resueltos"] == 1
    e2 = por_id(m, "EST-02")
    assert e2["ejercicios_abordados"] == 1 and e2["ejercicios_resueltos"] == 0
    assert m["curso"]["ejercicios_abordados"] == 2 and m["curso"]["resoluciones"] == 1


def test_orientacion_vs_respuesta(m):
    e1 = por_id(m, "EST-01")
    assert e1["pedidos"] == {"orientacion": 3, "respuesta": 1, "verificacion": 1, "conversacion": 0}
    assert e1["proporcion_orientacion"] == 0.75
    assert e1["proporcion_respuesta"] == 0.2
    assert m["curso"]["pedidos"]["orientacion"] == 5
    assert m["curso"]["metas_validos"] == 7 and m["curso"]["respuestas_tutor"] == 8


def test_errores_por_codigo(m):
    assert por_id(m, "EST-01")["errores"] == {"E05": 1, "E10": 1}
    assert por_id(m, "EST-02")["errores"] == {"E02": 1}
    assert {e["codigo"]: e["veces"] for e in m["errores"]} == {"E02": 1, "E05": 1, "E10": 1}


def test_escalon_promedio_alcanzado(m):
    # EST-01: SEP-01 llegó a 3, LIN-01 a 1 → 2. EST-02: SEP-01 llegó a 4.
    assert por_id(m, "EST-01")["escalon_promedio"] == 2.0
    assert por_id(m, "EST-02")["escalon_promedio"] == 4.0
    assert m["curso"]["escalon_promedio"] == round((3 + 1 + 4) / 3, 2)


def test_ejercicios_mas_trabados(m):
    primero, segundo = m["ejercicios"]
    assert primero["ejercicio"] == "SEP-01"
    assert primero == {"ejercicio": "SEP-01", "abordado_por": 2, "trabados": 2, "turnos_trabado": 3,
                       "resuelto_por": 1, "turnos": 6, "escalon_promedio": 3.5}
    assert segundo["ejercicio"] == "LIN-01" and segundo["trabados"] == 0


def test_indicador_de_costo(m):
    k = m["costo"]
    # Día: miércoles 11/11 en Buenos Aires → ninguno. Mes de noviembre: los 8.
    assert k["turnos_dia"] == 0 and k["turnos_mes"] == 8
    assert k["costo_mes_usd"] == round(8 * config.COSTO_MEDIO_TURNO_USD, 2)
    assert k["tope_mensual_usd"] == config.TOPE_MENSUAL_USD


def test_costo_del_dia_usa_la_hora_de_buenos_aires(doc, app_doc, reloj):
    bd = app_doc.state.bd
    # 23:30 del 3/11 en Buenos Aires = 02:30 UTC del 4/11.
    s = bd.abrir_sesion("EST-01", "celular", datetime(2026, 11, 4, 2, 30, tzinfo=timezone.utc))
    bd.guardar_turno(s, "EST-01", "a", "b", meta(), datetime(2026, 11, 4, 2, 30, tzinfo=timezone.utc))
    reloj.t = datetime(2026, 11, 4, 2, 45, tzinfo=timezone.utc)  # sigue siendo el 3/11 allá
    k = doc.get("/api/metricas", headers=DOC).json()["costo"]
    assert k["turnos_dia"] == 1
    reloj.t = datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc)  # ya es el 4/11
    assert doc.get("/api/metricas", headers=DOC).json()["costo"]["turnos_dia"] == 0


def test_costo_medio_configurable(doc, app_doc, ajustes_doc):
    poblar(app_doc.state.bd)
    ajustes_doc.costo_medio_turno = 0.5
    k = doc.get("/api/metricas", headers=DOC).json()["costo"]
    assert k["costo_medio_turno_usd"] == 0.5 and k["costo_mes_usd"] == 4.0
    assert k["proporcion_tope"] == round(4.0 / config.TOPE_MENSUAL_USD, 3)


def test_base_vacia(doc):
    m = doc.get("/api/metricas", headers=DOC).json()
    assert m["semanas"] == [] and m["ejercicios"] == [] and m["errores"] == []
    assert m["curso"]["turnos_por_sesion"] is None and m["costo"]["turnos_mes"] == 0


def test_metricas_con_turnos_reales_por_la_api(doc, app_doc, tutor):
    """De punta a punta: el <meta> que guarda /api/mensaje es el que lee el panel."""
    tok = doc.post("/api/login", json={"id": "EST-02", "codigo": "COD2AA"}, headers={"User-Agent": UA_PC}).json()["token"]
    tutor.respuestas = [
        "¿Qué te permite separar? " + f"<meta>{meta('HOM-01', escalon=1)}</meta>",
        "¿Dónde quedó la $K$? " + f"<meta>{meta('HOM-01', escalon=2, error='E08', estado='trabado')}</meta>",
    ]
    for texto in ("Tengo $y' = \\frac{2x + y}{x}$", "Pista"):
        assert doc.post("/api/mensaje", json={"texto": texto}, headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    m = doc.get("/api/metricas", headers=DOC).json()
    e2 = por_id(m, "EST-02")
    assert e2["turnos"] == 2 and e2["dispositivos"]["computadora"] == 1
    assert e2["errores"] == {"E08": 1} and e2["lista_abordados"] == ["HOM-01"]
    assert m["ejercicios"][0]["ejercicio"] == "HOM-01" and m["ejercicios"][0]["trabados"] == 1


# ---------- conversación ----------

def test_conversacion_completa(doc, app_doc):
    poblar(app_doc.state.bd)
    r = doc.get("/api/metricas/conversacion/est-01", headers=DOC)
    assert r.status_code == 200
    c = r.json()
    assert c["id"] == "EST-01" and len(c["sesiones"]) == 3
    s1 = c["sesiones"][0]
    assert s1["inicio"] == "2026-11-03 15:00" and s1["minutos"] == 10 and s1["turnos"] == 3
    assert s1["dispositivo"] == "celular"
    roles = [msg["rol"] for msg in s1["mensajes"]]
    assert roles == ["user", "assistant"] * 3
    assert s1["mensajes"][2]["pista"] is True
    assert s1["mensajes"][3]["meta"]["estado"] == "trabado"
    assert s1["mensajes"][0]["meta"] is None
    assert c["sesiones"][2]["mensajes"][3]["meta"] is None  # respuesta sin meta


def test_conversacion_de_estudiante_inexistente(doc):
    assert doc.get("/api/metricas/conversacion/EST-30", headers=DOC).status_code == 404
    assert doc.get("/api/metricas/conversacion/Juan", headers=DOC).status_code == 404
    c = doc.get("/api/metricas/conversacion/EST-03", headers=DOC).json()
    assert c["sesiones"] == []


# ---------- CSV ----------

def leer_csv(r):
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    texto = r.content.decode("utf-8")
    assert texto.startswith("﻿")
    return list(csv.reader(io.StringIO(texto[1:]), delimiter=";"))


@pytest.mark.parametrize("tabla", ["estudiantes", "curso", "semanas", "ejercicios", "errores", "costo", "sesiones", "mensajes"])
def test_csv_de_cada_tabla(doc, app_doc, tabla):
    poblar(app_doc.state.bd)
    filas = leer_csv(doc.get(f"/api/metricas/csv/{tabla}", headers=DOC))
    assert len(filas) >= 2


def test_csv_tabla_inexistente(doc):
    assert doc.get("/api/metricas/csv/otra", headers=DOC).status_code == 404


def test_csv_estudiantes_contenido(doc, app_doc):
    poblar(app_doc.state.bd)
    filas = leer_csv(doc.get("/api/metricas/csv/estudiantes", headers=DOC))
    enc = filas[0]
    e1 = dict(zip(enc, filas[1]))
    assert e1["estudiante"] == "EST-01" and e1["ingresos"] == "3" and e1["minutos_conectados"] == "46"
    assert e1["proporcion_orientacion"] == "0,75" and e1["E05"] == "1" and e1["E10"] == "1"
    assert e1["abordados"] == "LIN-01 SEP-01" and e1["resueltos"] == "SEP-01"
    assert len(filas) == 4  # encabezado + 3 estudiantes


def test_csv_semanas_y_mensajes(doc, app_doc, reloj):
    poblar(app_doc.state.bd)
    sem = leer_csv(doc.get("/api/metricas/csv/semanas", headers=DOC))
    assert sem[0] == ["estudiante", "semana_2026-11-02", "semana_2026-11-09", "total"]
    assert sem[-1] == ["CURSO", "3", "2", "5"]
    msj = leer_csv(doc.get("/api/metricas/csv/mensajes", headers=DOC))
    assert msj[0][:6] == ["mensaje", "sesion", "estudiante", "creado", "rol", "texto"]
    tutor = dict(zip(msj[0], msj[2]))
    assert tutor["rol"] == "tutor" and tutor["ejercicio"] == "SEP-01" and tutor["escalon"] == "1"


def test_csv_neutraliza_formulas(doc, app_doc):
    bd = app_doc.state.bd
    s = bd.abrir_sesion("EST-01", "celular", T0)
    bd.guardar_turno(s, "EST-01", '=HYPERLINK("http://x")', "-y es la respuesta", meta(), T0)
    msj = leer_csv(doc.get("/api/metricas/csv/mensajes", headers=DOC))
    textos = [dict(zip(msj[0], f))["texto"] for f in msj[1:]]
    assert textos == ["'=HYPERLINK(\"http://x\")", "'-y es la respuesta"]


def test_el_panel_no_cambia_lo_que_ve_el_estudiante(doc, app_doc):
    """Las rutas nuevas no exponen el metadato por el lado del estudiante."""
    poblar(app_doc.state.bd)
    tok = doc.post("/api/login", json={"id": "EST-01", "codigo": "COD1AA"}, headers={"User-Agent": UA_CELULAR}).json()["token"]
    h = doc.get("/api/historial", headers={"Authorization": f"Bearer {tok}"})
    assert h.status_code == 200 and "escalon" not in h.text and "meta" not in h.text


def test_calcular_directo_sin_app(tmp_path):
    from server.db import BaseDatos
    bd = BaseDatos(tmp_path / "t.db")
    bd.guardar_estudiante("EST-01", "x")
    poblar_minimo = bd.abrir_sesion("EST-01", "celular", T0)
    bd.guardar_turno(poblar_minimo, "EST-01", "a", "b", meta(escalon=2), T0 + timedelta(minutes=1))
    m = metricas.calcular(bd, T0 + timedelta(minutes=5), costo_turno=0.01, tope_mensual=100)
    assert m["costo"]["turnos_dia"] == 1 and m["costo"]["costo_dia_usd"] == 0.01
    assert m["generado"] == "2026-11-03 15:05"
