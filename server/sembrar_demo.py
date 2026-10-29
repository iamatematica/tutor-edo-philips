"""Base de demostración: 35 estudiantes con sus códigos y datos de prueba para el panel.

    python -m server.sembrar_demo              # crea datos/tutor.db e imprime los códigos
    python -m server.sembrar_demo --si-vacia   # no hace nada si la base ya tiene estudiantes
    python -m server.sembrar_demo --codigos    # solo imprime los códigos, sin tocar la base

Las sesiones y los mensajes son los mismos datos inventados que usó la Fase 3 para
las capturas del panel (semilla 3: 107 sesiones, 509 turnos, del 2 al 18 de
noviembre de 2026; EST-13 y EST-29 nunca entraron, así que sirven para probar el
chat en vivo con el historial vacío).

Los códigos se derivan de CODIGOS_SECRETO o, si no está definida, de un secreto fijo
de demostración: son siempre los mismos, en la computadora y en el Space. Por eso
esta base es solo para mostrar el sistema, nunca para el curso real.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone

from . import acceso, config
from .db import BaseDatos

log = logging.getLogger("tutor.demo")

SECRETO_DEMO = "demo-escuela-philips"

# Datos de prueba de la Fase 3 (no cambiar: el panel de las capturas sale de acá).
SEMILLA = 3
T0 = datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)
EJERCICIOS = ["SEP-01", "SEP-02", "LIN-01", "LIN-02", "HOM-01", "FIS-03", "FIS-05", "SIN-01", "CLA-01"]
SIN_INGRESOS = (13, 29)
TEXTOS_ESTUDIANTE = ["Pista", "Tengo $y' = 2xy$", "me da $y = e^{x^2} + C$", "pasame la respuesta"]
TEXTOS_TUTOR = [
    "¿Qué tipo de ecuación es? ¿Qué te permite separar?",
    "Mirá la constante: $$e^{x^2 + C} = e^{x^2}\\cdot e^{C}$$ ¿qué pasa con $e^C$?",
    "Te queda planteada $\\int \\frac{1}{y}\\,dy = \\int 2x\\,dx$. Escribí tu intento.",
]


def codigos(ajustes: config.Ajustes) -> list[tuple[str, str]]:
    secreto = ajustes.codigos_secreto or SECRETO_DEMO
    return [(acceso.id_estudiante(i), acceso.codigo_derivado(secreto, acceso.id_estudiante(i)))
            for i in range(1, ajustes.n_estudiantes + 1)]


def esta_vacia(bd: BaseDatos) -> bool:
    return not bd.ids_estudiantes()


def sembrar(bd: BaseDatos, ajustes: config.Ajustes) -> list[tuple[str, str]]:
    """Carga estudiantes, sesiones y mensajes de demostración. Devuelve [(EST-NN, código)]."""
    lista = codigos(ajustes)
    for est, codigo in lista:
        bd.guardar_estudiante(est, acceso.hash_codigo(codigo))

    # El mismo generador, en el mismo orden, que el script de la Fase 3.
    rng = random.Random(SEMILLA)
    for i in range(1, 36):
        est = acceso.id_estudiante(i)
        if i in SIN_INGRESOS:
            continue
        for _ in range(rng.randint(1, 6)):
            t = T0 + timedelta(days=rng.randint(0, 16), hours=rng.randint(0, 5))
            sesion = bd.abrir_sesion(est, rng.choice(["celular"] * 3 + ["computadora"]), t)
            ejercicio = rng.choice(EJERCICIOS)
            escalon = 0
            for _ in range(rng.randint(0, 9)):
                t += timedelta(minutes=rng.randint(1, 4))
                tipo = rng.choices(["orientacion", "respuesta", "verificacion", "conversacion"], [6, 1, 2, 1])[0]
                if tipo == "orientacion":
                    escalon = min(4, escalon + 1)
                estado = rng.choices(["avanzando", "trabado", "resuelto_por_estudiante"], [6, 2, 1])[0]
                error = rng.choice([None] * 5 + ["E02", "E05", "E07", "E03", "E09"])
                meta = {"ejercicio": ejercicio, "tipo_pedido": tipo,
                        "escalon": escalon if tipo == "orientacion" else 0,
                        "error_detectado": error, "estado": estado}
                texto = rng.choice(TEXTOS_ESTUDIANTE)
                respuesta = rng.choice(TEXTOS_TUTOR)
                bd.guardar_turno(sesion, est, texto, respuesta, json.dumps(meta), t)
    return lista


def hoja(lista: list[tuple[str, str]]) -> str:
    lineas = ["Modo demostración · códigos de acceso (datos inventados, no usar en el curso)"]
    lineas += [f"  {est}  {acceso.formatear_codigo(codigo)}" for est, codigo in lista]
    return "\n".join(lineas)


def sembrar_si_vacia(ajustes: config.Ajustes, bd: BaseDatos | None = None) -> bool:
    """Siembra la base demo si no tiene estudiantes. Devuelve True si sembró."""
    bd = bd or BaseDatos(ajustes.db)
    if not esta_vacia(bd):
        return False
    lista = sembrar(bd, ajustes)
    log.info("Base de demostración sembrada en %s.\n%s", ajustes.db, hoja(lista))
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--si-vacia", action="store_true", help="no hacer nada si la base ya tiene estudiantes")
    p.add_argument("--codigos", action="store_true", help="solo imprimir los códigos, sin tocar la base")
    args = p.parse_args(argv)

    ajustes = config.Ajustes()
    if args.codigos:
        print(hoja(codigos(ajustes)))
        return 0
    bd = BaseDatos(ajustes.db)
    if not esta_vacia(bd):
        if args.si_vacia:
            print(f"{ajustes.db} ya tiene estudiantes: no se siembra nada.")
            return 0
        print(f"{ajustes.db} ya tiene datos. La base demo se crea solo sobre una base vacía: "
              "borrá ese archivo (si es de prueba) o usá otra carpeta con TUTOR_DATOS.", file=sys.stderr)
        return 1
    lista = sembrar(bd, ajustes)
    print(f"Base de demostración creada en {ajustes.db}.\n")
    print(hoja(lista))
    print("\nPara chatear con el historial vacío, entrá como EST-13 o EST-29.")
    print("Panel docente: /panel. Con TUTOR_DEMO=1 y sin DOCENTE_KEY definida, la clave es «demo».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
