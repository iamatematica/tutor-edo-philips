from server import acceso, config
from server.app import crear_app
from server.db import BaseDatos
from server.generar_codigos import escribir_hoja, generar


def test_normalizar_id():
    for entrada in ["EST-07", "est07", "EST 7", "7", " est-7 ", "07"]:
        assert acceso.normalizar_id(entrada) == "EST-07", entrada
    for entrada in ["", "EST-", "0", "abc", "EST-123", "Juan"]:
        assert acceso.normalizar_id(entrada) is None, entrada


def test_hash_y_verificacion():
    h = acceso.hash_codigo("ABC234")
    assert "ABC234" not in h
    assert acceso.verificar_codigo("abc-234", h)
    assert acceso.verificar_codigo(" ABC 234 ", h)
    assert not acceso.verificar_codigo("ABC235", h)
    assert not acceso.verificar_codigo("ABC234", "basura")


def test_codigos_sin_caracteres_ambiguos():
    for _ in range(200):
        c = acceso.codigo_aleatorio()
        assert len(c) == 6 and not set(c) & set("0O1IL5S")


def test_generar_crea_35_y_no_repite(tmp_path):
    aj = config.Ajustes(datos=tmp_path, codigos_secreto=None)
    nuevos = generar(aj, 35)
    assert [e for e, _ in nuevos] == [f"EST-{i:02d}" for i in range(1, 36)]
    assert len({c for _, c in nuevos}) == 35
    bd = BaseDatos(aj.db)
    est, codigo = nuevos[6]
    assert acceso.verificar_codigo(codigo, bd.codigo_hash(est))
    # Segunda corrida: nada nuevo, los códigos anteriores siguen valiendo.
    assert generar(aj, 35) == []
    assert acceso.verificar_codigo(codigo, bd.codigo_hash(est))
    # --regenerar invalida los viejos.
    otra = dict(generar(aj, 35, regenerar=True))
    assert len(otra) == 35
    assert acceso.verificar_codigo(otra[est], bd.codigo_hash(est))


def test_hoja_para_imprimir(tmp_path):
    aj = config.Ajustes(datos=tmp_path, codigos_secreto=None)
    nuevos = generar(aj, 3)
    escribir_hoja(aj, nuevos)
    hoja = (tmp_path / "codigos.txt").read_text(encoding="utf-8")
    for est, codigo in nuevos:
        assert est in hoja and acceso.formatear_codigo(codigo) in hoja


def test_secreto_deriva_los_mismos_codigos_que_siembra_el_server(tmp_path):
    aj = config.Ajustes(datos=tmp_path / "a", system_prompt=tmp_path / "x.md", codigos_secreto="secreto-del-profe")
    codigos = dict(generar(aj, 35))
    assert codigos["EST-12"] == acceso.codigo_derivado("secreto-del-profe", "EST-12")
    assert codigos["EST-12"] != acceso.codigo_derivado("otro", "EST-12")

    # El server, con el mismo secreto y otra base, arma la tabla solo.
    aj_server = config.Ajustes(datos=tmp_path / "b", system_prompt=tmp_path / "x.md", codigos_secreto="secreto-del-profe")
    app = crear_app(aj_server, responder=lambda s, m: ("", ""))
    bd = app.state.bd
    assert len(bd.ids_estudiantes()) == 35
    assert acceso.verificar_codigo(codigos["EST-12"], bd.codigo_hash("EST-12"))
