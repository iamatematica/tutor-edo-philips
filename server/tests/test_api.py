import sqlite3

from server.claude import ErrorTutor
from server.tests.conftest import META_OK


def test_salud(cliente):
    assert cliente.get("/api/salud").json() == {"ok": True}


def test_front_se_sirve(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "Escuela Philips" in r.text


def test_login_ok_y_normaliza_id(cliente):
    r = cliente.post("/api/login", json={"id": "7", "codigo": "abc-234"})
    assert r.status_code == 200
    assert r.json()["id"] == "EST-07" and len(r.json()["token"]) > 20


def test_login_falla(cliente):
    assert cliente.post("/api/login", json={"id": "EST-07", "codigo": "ZZZZZZ"}).status_code == 401
    assert cliente.post("/api/login", json={"id": "EST-30", "codigo": "ABC234"}).status_code == 401
    assert cliente.post("/api/login", json={"id": "Juan", "codigo": "ABC234"}).status_code == 400


def test_login_se_bloquea_tras_varios_fallos(cliente):
    for _ in range(5):
        assert cliente.post("/api/login", json={"id": "EST-08", "codigo": "MAL"}).status_code == 401
    r = cliente.post("/api/login", json={"id": "EST-08", "codigo": "XYZ789"})
    assert r.status_code == 429
    # El bloqueo es por identificador: otro estudiante entra igual.
    assert cliente.post("/api/login", json={"id": "EST-07", "codigo": "ABC234"}).status_code == 200


def test_rutas_protegidas(cliente):
    assert cliente.get("/api/historial").status_code == 401
    assert cliente.post("/api/mensaje", json={"texto": "hola"}).status_code == 401
    malo = {"Authorization": "Bearer inventado"}
    assert cliente.get("/api/historial", headers=malo).status_code == 401


def test_logout_invalida_token(cliente, auth):
    assert cliente.post("/api/logout", headers=auth).status_code == 200
    assert cliente.get("/api/historial", headers=auth).status_code == 401


def test_mensaje_oculta_meta_y_lo_guarda(cliente, auth, app, tutor):
    tutor.respuestas = ["¿Qué te permite separar? " + META_OK]
    r = cliente.post("/api/mensaje", json={"texto": "Tengo y' = 2xy"}, headers=auth)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["respuesta"] == "¿Qué te permite separar?"
    assert "meta" not in r.text and "escalon" not in r.text and "orientacion" not in r.text
    assert cuerpo["etiqueta_pista"] == "Otra pista"

    with sqlite3.connect(app.state.ajustes.db) as c:
        c.row_factory = sqlite3.Row
        filas = c.execute("SELECT * FROM mensajes ORDER BY id").fetchall()
    assert [f["rol"] for f in filas] == ["user", "assistant"]
    assert filas[0]["texto"] == "Tengo y' = 2xy"
    t = filas[1]
    assert t["ejercicio"] == "sep-01" and t["tipo_pedido"] == "orientacion" and t["escalon"] == 1
    assert t["estado"] == "avanzando" and t["error_detectado"] is None and t["meta_valido"] == 1
    assert "<meta>" in t["texto_crudo"] and t["modelo"] == "modelo-de-prueba"


def test_system_prompt_y_contexto(cliente, auth, app, tutor):
    cliente.post("/api/mensaje", json={"texto": "primero"}, headers=auth)
    cliente.post("/api/mensaje", json={"texto": "segundo"}, headers=auth)
    system, mensajes = tutor.llamadas[-1]
    assert system == app.state.system_prompt
    assert [m["role"] for m in mensajes] == ["user", "assistant", "user"]
    assert mensajes[0]["content"] == "primero" and mensajes[-1]["content"] == "segundo"
    # Al modelo vuelve el texto visible, sin el bloque <meta> anterior.
    assert "<meta>" not in mensajes[1]["content"]


def test_historial_sin_meta(cliente, auth, tutor):
    tutor.respuestas = ["Bien, seguí. " + META_OK]
    cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth)
    r = cliente.get("/api/historial", headers=auth)
    assert r.status_code == 200
    h = r.json()
    assert h["id"] == "EST-07"
    assert [(m["rol"], m["texto"]) for m in h["mensajes"]] == [("user", "hola"), ("assistant", "Bien, seguí.")]
    assert "meta" not in r.text and "escalon" not in r.text and "sep-01" not in r.text


def test_historial_es_por_estudiante(cliente, auth):
    cliente.post("/api/mensaje", json={"texto": "soy el 7"}, headers=auth)
    t8 = cliente.post("/api/login", json={"id": "EST-08", "codigo": "XYZ789"}).json()["token"]
    h8 = cliente.get("/api/historial", headers={"Authorization": f"Bearer {t8}"}).json()
    assert h8["mensajes"] == [] and h8["etiqueta_pista"] == "Pista"


def test_boton_pista(cliente, auth, tutor):
    r = cliente.post("/api/mensaje", json={"texto": "", "pista": True}, headers=auth)
    assert r.status_code == 200
    assert tutor.llamadas[-1][1][-1] == {"role": "user", "content": "Pista"}
    m = cliente.get("/api/historial", headers=auth).json()["mensajes"][0]
    assert m == {**m, "rol": "user", "texto": "Pista", "pista": True}


def test_etiqueta_vuelve_a_pista_al_resolver(cliente, auth, tutor):
    tutor.respuestas = ["¡Eso es! " + META_OK.replace('"avanzando"', '"resuelto_por_estudiante"')]
    r = cliente.post("/api/mensaje", json={"texto": "me dio y = K e^{x^2}"}, headers=auth)
    assert r.json()["etiqueta_pista"] == "Pista"


def test_mensaje_vacio_o_largo(cliente, auth, tutor):
    assert cliente.post("/api/mensaje", json={"texto": "   "}, headers=auth).status_code == 422
    assert cliente.post("/api/mensaje", json={"texto": "x" * 2001}, headers=auth).status_code == 422
    assert tutor.llamadas == []


def test_meta_ausente_igual_responde(cliente, auth, app, tutor):
    tutor.respuestas = ["Contame qué probaste."]
    r = cliente.post("/api/mensaje", json={"texto": "no sé"}, headers=auth)
    assert r.status_code == 200 and r.json()["respuesta"] == "Contame qué probaste."
    fila = app.state.bd.ultimo_del_tutor("EST-07")
    assert fila["meta_valido"] == 0 and fila["escalon"] is None


def test_error_de_claude_no_guarda_nada(cliente, auth, app, tutor):
    tutor.error = ErrorTutor("limite")
    r = cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth)
    assert r.status_code == 503 and "minuto" in r.json()["detail"]
    assert app.state.bd.mensajes("EST-07") == []
    # Al reintentar, la conversación sigue alternando bien.
    tutor.error = None
    cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth)
    assert [m["role"] for m in tutor.llamadas[-1][1]] == ["user"]


def test_respuesta_solo_meta_es_error(cliente, auth, app, tutor):
    tutor.respuestas = [META_OK]
    assert cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth).status_code == 502
    assert app.state.bd.mensajes("EST-07") == []


def test_placeholder_si_no_hay_prompt(app):
    assert app.state.prompt_placeholder
    assert "<meta>" in app.state.system_prompt


def test_lee_tutor_system_prompt(tmp_path, ajustes, tutor):
    from server.app import crear_app

    ruta = tmp_path / "system_prompt.md"
    ruta.write_text("Sos el tutor.", encoding="utf-8")
    ajustes.system_prompt = ruta
    app = crear_app(ajustes, responder=tutor)
    assert app.state.system_prompt == "Sos el tutor." and not app.state.prompt_placeholder


def test_sin_datos_personales_en_el_esquema(app):
    with sqlite3.connect(app.state.ajustes.db) as c:
        columnas = {f[1] for f in c.execute("PRAGMA table_info(estudiantes)")}
    assert columnas == {"id", "codigo_hash"}
