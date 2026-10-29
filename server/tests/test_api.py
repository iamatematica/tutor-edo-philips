import json
import sqlite3
from datetime import datetime, timezone

from server import acceso, config
from server.claude import ErrorTutor
from server.tests.conftest import META_OK, UA_PC


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


def test_token_vence_y_se_invalida_al_regenerar_codigo(cliente, auth, app, reloj):
    assert cliente.post("/api/logout", headers=auth).status_code == 200
    assert cliente.get("/api/historial", headers=auth).status_code == 200
    # Token alterado.
    roto = {"Authorization": auth["Authorization"][:-1] + ("0" if auth["Authorization"][-1] != "0" else "1")}
    assert cliente.get("/api/historial", headers=roto).status_code == 401
    # Regenerar el código del estudiante invalida su ingreso.
    app.state.bd.guardar_estudiante("EST-07", acceso.hash_codigo("NUEVO2"))
    assert cliente.get("/api/historial", headers=auth).status_code == 401


def test_token_vence_a_la_semana(cliente, auth, reloj):
    reloj.avanzar(days=6)
    assert cliente.get("/api/historial", headers=auth).status_code == 200
    reloj.avanzar(days=2)
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
        meta = c.execute(
            "SELECT json_extract(meta_json, '$.ejercicio') AS ej, json_extract(meta_json, '$.escalon') AS esc "
            "FROM mensajes WHERE rol = 'assistant'"
        ).fetchone()
    assert [f["rol"] for f in filas] == ["user", "assistant"]
    assert filas[0]["texto"] == "Tengo y' = 2xy" and filas[0]["meta_json"] is None
    assert filas[1]["texto"] == "¿Qué te permite separar?"
    assert json.loads(filas[1]["meta_json"]) == {
        "ejercicio": "sep-01", "tipo_pedido": "orientacion", "escalon": 1,
        "error_detectado": None, "estado": "avanzando",
    }
    assert (meta["ej"], meta["esc"]) == ("sep-01", 1)
    assert filas[0]["sesion"] == filas[1]["sesion"] and filas[0]["estudiante"] == "EST-07"


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
    assert fila["meta_json"] is None


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


def test_esquema_del_contrato(app):
    """Exactamente las tablas y columnas de CLAUDE.md: nada de nombres ni IP."""
    with sqlite3.connect(app.state.ajustes.db) as c:
        tablas = {t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'")} - {"sqlite_sequence"}
        columnas = {t: {f[1] for f in c.execute(f"PRAGMA table_info({t})")} for t in tablas}
    assert columnas == {
        "estudiantes": {"id", "codigo_hash"},
        "sesiones": {"id", "estudiante", "inicio", "ultima_actividad", "dispositivo"},
        "mensajes": {"id", "sesion", "estudiante", "rol", "texto", "meta_json", "creado"},
    }


def test_login_abre_sesion_con_dispositivo(cliente, app):
    cliente.post("/api/login", json={"id": "EST-07", "codigo": "ABC234"})
    cliente.post("/api/login", json={"id": "EST-07", "codigo": "ABC234"}, headers={"User-Agent": UA_PC})
    sesiones = app.state.bd.sesiones("EST-07")
    assert [s["dispositivo"] for s in sesiones] == ["celular", "computadora"]
    assert sesiones[0]["inicio"] == sesiones[0]["ultima_actividad"] == "2026-11-03T18:00:00+00:00"


def test_mensaje_actualiza_ultima_actividad(cliente, auth, app, reloj):
    reloj.avanzar(minutes=5)
    cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth)
    reloj.avanzar(minutes=15)
    cliente.post("/api/mensaje", json={"texto": "sigo"}, headers=auth)
    (s,) = app.state.bd.sesiones("EST-07")
    assert s["inicio"] == "2026-11-03T18:00:00+00:00"
    assert s["ultima_actividad"] == "2026-11-03T18:20:00+00:00"


def test_sesion_nueva_tras_20_minutos(cliente, auth, app, tutor, reloj):
    cliente.post("/api/mensaje", json={"texto": "primera sesión"}, headers=auth)
    reloj.avanzar(minutes=21)
    cliente.post("/api/mensaje", json={"texto": "volví"}, headers=auth)
    sesiones = app.state.bd.sesiones("EST-07")
    assert len(sesiones) == 2 and sesiones[1]["dispositivo"] == "celular"
    # A la API no va la conversación de la sesión anterior...
    assert tutor.llamadas[-1][1] == [{"role": "user", "content": "volví"}]
    # ...pero el estudiante ve todo su historial.
    textos = [m["texto"] for m in cliente.get("/api/historial", headers=auth).json()["mensajes"]]
    assert textos[0] == "primera sesión" and textos[2] == "volví"


def test_memoria_acotada_a_12_turnos(cliente, auth, tutor, reloj):
    for i in range(15):
        reloj.avanzar(minutes=1)
        cliente.post("/api/mensaje", json={"texto": f"m{i}"}, headers=auth)
    mensajes = tutor.llamadas[-1][1]
    assert len(mensajes) == 2 * 12 + 1
    assert mensajes[0] == {"role": "user", "content": "m2"}
    assert mensajes[-1] == {"role": "user", "content": "m14"}
    assert [m["role"] for m in mensajes] == ["user", "assistant"] * 12 + ["user"]


def test_limite_diario(cliente, auth, app, tutor, reloj):
    app.state.ajustes.limite_turnos_dia = 3
    for i in range(3):
        reloj.avanzar(minutes=1)
        assert cliente.post("/api/mensaje", json={"texto": f"m{i}"}, headers=auth).json()["limite_alcanzado"] is False
    r = cliente.post("/api/mensaje", json={"texto": "uno más"}, headers=auth).json()
    assert r["limite_alcanzado"] is True and "mañana" in r["respuesta"]
    assert len(tutor.llamadas) == 3  # no se llamó a la API
    assert len(app.state.bd.mensajes("EST-07")) == 6  # ni se guardó nada
    # 23:59 de Buenos Aires (02:59 UTC del día siguiente): sigue el límite.
    reloj.t = datetime(2026, 11, 4, 2, 59, tzinfo=timezone.utc)
    assert cliente.post("/api/mensaje", json={"texto": "x"}, headers=auth).json()["limite_alcanzado"] is True
    # 0:00 de Buenos Aires (03:00 UTC): se reinicia.
    reloj.t = datetime(2026, 11, 4, 3, 0, tzinfo=timezone.utc)
    assert cliente.post("/api/mensaje", json={"texto": "x"}, headers=auth).json()["limite_alcanzado"] is False


def test_limite_es_por_estudiante(cliente, auth, app):
    app.state.ajustes.limite_turnos_dia = 1
    cliente.post("/api/mensaje", json={"texto": "hola"}, headers=auth)
    t8 = cliente.post("/api/login", json={"id": "EST-08", "codigo": "XYZ789"}).json()["token"]
    r = cliente.post("/api/mensaje", json={"texto": "hola"}, headers={"Authorization": f"Bearer {t8}"})
    assert r.json()["limite_alcanzado"] is False


def test_secreto_de_sesion_se_guarda_en_datos(tmp_path, tutor):
    from server.app import crear_app

    aj = config.Ajustes(datos=tmp_path / "d", system_prompt=tmp_path / "x.md", codigos_secreto=None, sesion_secreto=None)
    crear_app(aj, responder=tutor)
    secreto = (tmp_path / "d" / "secreto_sesion").read_text()
    crear_app(aj, responder=tutor)
    assert (tmp_path / "d" / "secreto_sesion").read_text() == secreto and len(secreto) == 64
