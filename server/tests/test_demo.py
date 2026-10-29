"""Modo demostración: tutor guionado, siembra de la base demo y arranque con TUTOR_DEMO=1."""
import json
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

from server import acceso, config, sembrar_demo
from server.app import crear_app
from server.claude import ClienteClaude
from server.demo import MODELO_DEMO, TutorGuionado, cargar_banco, normalizar_ecuacion
from server.meta import extraer
from server.tests.conftest import UA_CELULAR

BANCO = config.RAIZ / "tutor" / "banco"


@pytest.fixture(scope="module")
def guion():
    return TutorGuionado(BANCO)


class Charla:
    """Conversación con el tutor guionado, con la misma ventana de 12 turnos del server."""

    def __init__(self, tutor):
        self.tutor = tutor
        self.mensajes: list[dict] = []

    def decir(self, texto: str) -> dict:
        contexto = self.mensajes[-2 * config.MAX_TURNOS_CONTEXTO:] + [{"role": "user", "content": texto}]
        crudo, modelo = self.tutor(None, contexto)
        assert modelo == MODELO_DEMO
        r = extraer(crudo)
        assert r["meta_valido"], crudo
        assert "<meta" not in r["texto"]
        self.mensajes += [{"role": "user", "content": texto}, {"role": "assistant", "content": r["texto"]}]
        return r


def primera(guion, id_plantilla):
    return next(e for e in guion.ejercicios if e.id == id_plantilla)


# ---------- banco ----------

def test_banco_carga_todas_las_instancias(guion):
    ids = {e.id for e in guion.ejercicios}
    assert len(ids) == len(list(BANCO.glob("*.yaml")))
    assert all(len(e.pistas) == 4 and e.enunciado for e in guion.ejercicios)


def test_render_igual_al_del_banco():
    """Sin SymPy en el server, los textos tienen que salir idénticos a los de tutor/banco/banco.py."""
    pytest.importorskip("sympy")
    sys.path.insert(0, str(BANCO))
    import banco

    referencia = {}
    for p in banco.cargar_plantillas():
        for v in banco.instancias(p):
            inst = banco.Instancia(p, v)
            referencia[(p["id"], inst.texto("enunciado"))] = list(inst.pistas().values())
    propios = {(e.id, e.enunciado): e.pistas for e in cargar_banco(BANCO)}
    assert propios == referencia


# ---------- escalera ----------

def test_escalera_un_escalon_por_pedido_y_no_avanza_despues_de_p4(guion):
    c = Charla(guion)
    r = c.decir("hola")
    ej = guion.ejercicios[0]
    assert ej.enunciado in r["texto"] and r["meta"]["ejercicio"] == ej.id and r["meta"]["escalon"] == 0
    for n in range(1, 5):
        r = c.decir("Pista")
        assert r["texto"] == ej.pistas[n - 1]
        assert r["meta"] == {"ejercicio": ej.id, "tipo_pedido": "orientacion", "escalon": n,
                             "error_detectado": None, "estado": "trabado" if n > 1 else "avanzando"}
    for _ in range(3):
        r = c.decir("Pista")
        assert r["meta"]["escalon"] == 4
        assert ej.pistas[3] in r["texto"] and "intento" in r["texto"]


def test_pedido_de_ayuda_en_palabras_tambien_sube_un_escalon(guion):
    c = Charla(guion)
    c.decir("y' = 2xy")
    r = c.decir("no sé cómo seguir")
    assert r["meta"]["escalon"] == 2 and r["meta"]["tipo_pedido"] == "orientacion"


def test_pista_sin_ejercicio_propone_uno_del_banco(guion):
    r = Charla(guion).decir("Pista")
    ej = guion.ejercicios[0]
    assert ej.enunciado in r["texto"] and ej.pistas[0] in r["texto"]
    assert r["meta"]["escalon"] == 1


def test_pedido_de_respuesta_no_la_da_y_no_saltea_escalones(guion):
    c = Charla(guion)
    c.decir("y' + 2y = 6")
    r = c.decir("pasame la respuesta")
    lin = primera(guion, "LIN-01")
    assert r["meta"]["tipo_pedido"] == "respuesta" and r["meta"]["escalon"] == 2
    assert lin.pistas[1] in r["texto"] and lin.pistas[2] not in r["texto"]


def test_intento_recibe_comentario_generico(guion):
    c = Charla(guion)
    c.decir("y' = 2xy")
    c.decir("Pista")
    r = c.decir("me da $y = Ke^{x^2}$")
    assert r["meta"] == {"ejercicio": "SEP-01", "tipo_pedido": "verificacion", "escalon": 0,
                         "error_detectado": None, "estado": "avanzando"}
    assert "$y' = 2xy$" in r["texto"]
    assert "bien" not in r["texto"].lower().replace("bien que lo escribas", "")
    # Después del comentario, la escalera sigue donde estaba.
    assert c.decir("Pista")["meta"]["escalon"] == 3


def test_ecuacion_del_banco_arranca_con_la_primera_pista(guion):
    r = Charla(guion).decir("Tengo que resolver $y' = \\frac{3x + y}{x}$")
    hom = next(e for e in guion.ejercicios if e.id == "HOM-01" and "3x + y" in e.enunciado)
    assert r["meta"]["ejercicio"] == "HOM-01" and r["meta"]["escalon"] == 1
    assert hom.enunciado in r["texto"] and hom.pistas[0] in r["texto"]


def test_ecuacion_fuera_del_banco_recibe_una_del_banco(guion):
    r = Charla(guion).decir("y' + y = x")  # exige partes: no está en el banco
    assert "no está entre los ejercicios" in r["texto"]
    ej = next(e for e in guion.propuestas if e.id == r["meta"]["ejercicio"])
    assert ej.tema == "lineales" and ej.enunciado in r["texto"]
    assert "y' + y = x" not in r["texto"]


def test_otro_ejercicio_y_fuera_de_tema(guion):
    c = Charla(guion)
    c.decir("y' = 2xy")
    r = c.decir("dame otro ejercicio")
    assert r["meta"]["ejercicio"] not in (None, "SEP-01")
    r = c.decir("¿quién ganó el partido?")
    assert r["meta"]["tipo_pedido"] == "conversacion" and r["meta"]["escalon"] == 0
    r = c.decir("quiero un ejercicio de circuitos")
    assert r["meta"]["ejercicio"].startswith("FIS-")


def test_sigue_el_ejercicio_con_la_ventana_de_12_turnos(guion):
    c = Charla(guion)
    c.decir("y' = 2xy")
    c.decir("Pista")
    for i in range(14):
        c.decir("me da $y = e^{x^2} + C$")
    r = c.decir("Pista")
    assert r["meta"]["ejercicio"] == "SEP-01" and r["meta"]["escalon"] >= 1


def test_ninguna_respuesta_filtra_la_solucion_ni_usa_metalenguaje(guion):
    """Para cada instancia del banco: escalera completa, pedido de respuesta e intentos."""
    pytest.importorskip("sympy")
    sys.path.insert(0, str(config.RAIZ / "tutor" / "eval"))
    sys.path.insert(0, str(BANCO))
    import banco
    import detector
    from verificar_banco import Verificador

    verificador = Verificador.__new__(Verificador)
    edos = {}
    for p in banco.cargar_plantillas():
        if p.get("solucion_general"):
            for v in banco.instancias(p):
                inst = banco.Instancia(p, v)
                edos[(p["id"], inst.texto("enunciado"))] = verificador.edo_de(inst)

    revisadas = 0
    for ej in guion.ejercicios:
        c = Charla(guion)
        c.decir(f"Quiero hacer {ej.ecuacion}")
        textos = [c.decir(t)["texto"] for t in
                  ["Pista", "Pista", "pasame la respuesta", "Pista", "Pista", "me da algo así", "Pista"]]
        for t in textos:
            assert not detector.metalenguaje(t), t
            assert not detector.fracciones_en_linea(t), t
            assert not detector.herramientas_prohibidas(t), t
            if (ej.id, ej.enunciado) in edos:
                assert not detector.soluciones_en_texto(t, [edos[(ej.id, ej.enunciado)]]), t
        revisadas += 1
    assert revisadas == len(guion.ejercicios)


def test_normalizar_ecuacion():
    assert normalizar_ecuacion("$y' = 2xy$") == normalizar_ecuacion("y'=2*x*y")
    assert normalizar_ecuacion("dy/dx = 2xy") == normalizar_ecuacion("y' = 2xy")
    assert normalizar_ecuacion("$y' + \\frac{y}{x} = 3$") == normalizar_ecuacion("y' + y/x = 3")


# ---------- siembra ----------

def contar(db):
    c = sqlite3.connect(db)
    try:
        return {
            "estudiantes": c.execute("SELECT COUNT(*) FROM estudiantes").fetchone()[0],
            "sesiones": c.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0],
            "turnos": c.execute("SELECT COUNT(*) FROM mensajes WHERE rol = 'user'").fetchone()[0],
            "celular": c.execute("SELECT COUNT(*) FROM sesiones WHERE dispositivo = 'celular'").fetchone()[0],
            "sin_ingresos": [f[0] for f in c.execute(
                "SELECT id FROM estudiantes WHERE id NOT IN (SELECT estudiante FROM sesiones) ORDER BY id")],
            "metas": [json.loads(f[0]) for f in c.execute(
                "SELECT meta_json FROM mensajes WHERE rol = 'assistant'")],
        }
    finally:
        c.close()


@pytest.fixture
def ajustes_demo(ajustes):
    ajustes.demo = True
    ajustes.__post_init__()
    return ajustes


def test_siembra_reproduce_los_datos_de_la_fase_3(ajustes_demo):
    from server.db import BaseDatos

    bd = BaseDatos(ajustes_demo.db)
    lista = sembrar_demo.sembrar(bd, ajustes_demo)
    n = contar(ajustes_demo.db)
    assert n["estudiantes"] == 35 and len(lista) == 35
    assert (n["sesiones"], n["turnos"], n["celular"]) == (107, 509, 87)
    assert n["sin_ingresos"] == ["EST-13", "EST-29"]
    assert all(m["ejercicio"] in sembrar_demo.EJERCICIOS for m in n["metas"])
    # Cada código impreso sirve para entrar.
    for est, codigo in lista:
        assert acceso.verificar_codigo(codigo, bd.codigo_hash(est))


def test_comando_crea_imprime_y_no_pisa_una_base_con_datos(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TUTOR_DATOS", str(tmp_path / "d"))
    assert sembrar_demo.main(["--codigos"]) == 0
    assert not (tmp_path / "d" / "tutor.db").exists()
    codigos = capsys.readouterr().out
    assert "EST-35" in codigos

    assert sembrar_demo.main([]) == 0
    salida = capsys.readouterr().out
    assert "EST-01" in salida and "EST-13" in salida
    assert contar(tmp_path / "d" / "tutor.db")["turnos"] == 509
    # Los códigos son los mismos con --codigos y al sembrar.
    assert all(linea in salida for linea in codigos.splitlines()[1:])

    assert sembrar_demo.main([]) == 1          # no siembra sobre una base con datos
    assert sembrar_demo.main(["--si-vacia"]) == 0
    assert contar(tmp_path / "d" / "tutor.db")["turnos"] == 509


# ---------- server con TUTOR_DEMO ----------

def test_ajustes_demo_desde_el_entorno(monkeypatch):
    monkeypatch.setenv("TUTOR_DEMO", "1")
    monkeypatch.delenv("DOCENTE_KEY", raising=False)
    a = config.Ajustes()
    assert a.demo and a.docente_key == "demo"
    monkeypatch.setenv("DOCENTE_KEY", "otra-clave")
    assert config.Ajustes().docente_key == "otra-clave"
    monkeypatch.delenv("TUTOR_DEMO")
    monkeypatch.delenv("DOCENTE_KEY")
    a = config.Ajustes()
    assert not a.demo and a.docente_key is None


def test_sin_demo_no_cambia_nada(ajustes):
    app = crear_app(ajustes)
    assert isinstance(app.state.responder, ClienteClaude)
    assert app.state.bd.ids_estudiantes() == []
    assert TestClient(app).get("/api/salud").json() == {"ok": True}


def test_server_demo_de_punta_a_punta(ajustes_demo, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = crear_app(ajustes_demo)
    assert isinstance(app.state.responder, TutorGuionado)
    assert contar(ajustes_demo.db)["turnos"] == 509

    cli = TestClient(app, headers={"User-Agent": UA_CELULAR})
    assert cli.get("/api/salud").json() == {"ok": True, "demo": True, "clave_demo": True}

    codigo = dict(sembrar_demo.codigos(ajustes_demo))["EST-13"]
    token = cli.post("/api/login", json={"id": "EST-13", "codigo": codigo}).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}
    vistos = []
    for cuerpo in [{"pista": True}, {"pista": True}, {"texto": "me da $y = Ke^{x^2}$"}]:
        r = cli.post("/api/mensaje", json=cuerpo, headers=auth)
        assert r.status_code == 200
        vistos.append(r.json()["respuesta"])
    assert all("<meta" not in v and "escal" not in v.lower() for v in vistos)
    assert r.json()["etiqueta_pista"] == "Pista"  # el último turno fue un intento (escalón 0)

    metas = [json.loads(m["meta_json"]) for m in app.state.bd.mensajes("EST-13") if m["rol"] == "assistant"]
    assert [m["escalon"] for m in metas] == [1, 2, 0]
    assert [m["tipo_pedido"] for m in metas] == ["orientacion", "orientacion", "verificacion"]

    # El panel abre con la clave "demo" y ya tiene los datos sembrados más estos turnos.
    m = cli.get("/api/metricas", headers={"X-Docente-Key": "demo"})
    assert m.status_code == 200 and m.json()["curso"]["turnos"] == 512


def test_demo_no_resiembra_una_base_con_estudiantes(ajustes_demo):
    crear_app(ajustes_demo)
    crear_app(ajustes_demo)
    assert contar(ajustes_demo.db)["turnos"] == 509


def test_front_trae_el_cartel_de_demostracion():
    texto = "Modo demostración · respuestas guionadas, sin IA"
    for html in ["web/index.html", "panel/index.html"]:
        contenido = (config.RAIZ / html).read_text(encoding="utf-8")
        assert texto in contenido and 'id="cartel-demo"' in contenido
