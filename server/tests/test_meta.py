from server.meta import extraer

META = '{"ejercicio": "lin-02", "tipo_pedido": "respuesta", "escalon": 2, "error_detectado": "E10", "estado": "trabado"}'


def test_separa_texto_y_meta():
    r = extraer(f"Probá agrupar las $y$ de un lado.\n<meta>{META}</meta>")
    assert r["texto"] == "Probá agrupar las $y$ de un lado."
    assert r["meta_valido"]
    assert r["meta"] == {
        "ejercicio": "lin-02",
        "tipo_pedido": "respuesta",
        "escalon": 2,
        "error_detectado": "E10",
        "estado": "trabado",
    }


def test_sin_meta():
    r = extraer("Hola, ¿en qué ejercicio estás?")
    assert r["texto"] == "Hola, ¿en qué ejercicio estás?"
    assert r["meta"] is None and r["meta_json"] is None and not r["meta_valido"]


def test_meta_con_cerco_de_codigo_y_mayusculas():
    r = extraer(f"Bien.\n<META>\n```json\n{META}\n```\n</META>")
    assert r["texto"] == "Bien."
    assert r["meta_valido"]


def test_meta_invalido_se_oculta_igual():
    r = extraer('Seguí así. <meta>{"tipo_pedido": "cualquiera", "escalon": 9}</meta>')
    assert r["texto"] == "Seguí así."
    assert not r["meta_valido"]
    assert r["meta_json"] == '{"tipo_pedido": "cualquiera", "escalon": 9}'


def test_meta_json_roto():
    r = extraer("Texto <meta>{no es json</meta>")
    assert r["texto"] == "Texto" and not r["meta_valido"]


def test_meta_sin_cierre_no_se_muestra():
    r = extraer('Pensá en la derivada. <meta>{"ejercicio": nu')
    assert r["texto"] == "Pensá en la derivada."
    assert "meta" not in r["texto"]


def test_varios_bloques_usa_el_ultimo():
    otro = META.replace('"escalon": 2', '"escalon": 3')
    r = extraer(f"A <meta>{META}</meta> B <meta>{otro}</meta>")
    assert r["texto"] == "A  B"
    assert r["meta"]["escalon"] == 3


def test_validacion_de_campos():
    casos = [
        ('"escalon": 5', False),
        ('"escalon": true', False),
        ('"error_detectado": "E11"', False),
        ('"error_detectado": null', True),
        ('"ejercicio": null', True),
    ]
    for reemplazo, valido in casos:
        clave = reemplazo.split(":")[0]
        partes = [p if not p.strip().startswith(clave) else " " + reemplazo for p in META.strip("{}").split(",")]
        r = extraer("x <meta>{" + ",".join(partes) + "}</meta>")
        assert r["meta_valido"] is valido, reemplazo
