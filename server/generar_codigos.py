"""Genera los códigos de acceso EST-01 … EST-35 y los imprime para el docente.

    python -m server.generar_codigos              # crea los que falten
    python -m server.generar_codigos --regenerar  # códigos nuevos para todos
    python -m server.generar_codigos -n 40        # otra cantidad de estudiantes

En la base solo se guarda el hash de cada código. Los códigos en claro se
escriben una única vez en datos/codigos.txt (fuera del repo) para imprimir.

Si está definida la variable CODIGOS_SECRETO, los códigos se derivan de ese
secreto: son siempre los mismos, y el server, con el mismo secreto, arma solo
la tabla de estudiantes al arrancar (útil en Hugging Face Spaces, donde no hay
consola para correr este script).
"""
from __future__ import annotations

import argparse
from datetime import datetime

from . import acceso, config
from .db import BaseDatos


def generar(ajustes: config.Ajustes, n: int, regenerar: bool = False) -> list[tuple[str, str]]:
    """Devuelve [(EST-NN, código)] de los estudiantes creados o regenerados."""
    bd = BaseDatos(ajustes.db)
    existentes = set(bd.ids_estudiantes())
    nuevos = []
    for i in range(1, n + 1):
        est = acceso.id_estudiante(i)
        if est in existentes and not regenerar and not ajustes.codigos_secreto:
            continue
        if ajustes.codigos_secreto:
            codigo = acceso.codigo_derivado(ajustes.codigos_secreto, est)
        else:
            codigo = acceso.codigo_aleatorio()
        bd.guardar_estudiante(est, acceso.hash_codigo(codigo))
        nuevos.append((est, codigo))
    return nuevos


def escribir_hoja(ajustes: config.Ajustes, codigos: list[tuple[str, str]]) -> None:
    ruta = ajustes.datos / "codigos.txt"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    origen = "derivados de CODIGOS_SECRETO" if ajustes.codigos_secreto else "aleatorios"
    lineas = [
        f"Tutor de Ecuaciones Diferenciales · códigos de acceso ({origen})",
        f"Generados el {datetime.now():%d/%m/%Y %H:%M}",
        "Recortar por la línea y entregar a cada estudiante el suyo.",
        "",
    ]
    for est, codigo in codigos:
        lineas += [f"  Identificador: {est}    Código: {acceso.formatear_codigo(codigo)}", "  " + "-" * 50]
    modo = "a" if ruta.exists() else "w"
    with ruta.open(modo, encoding="utf-8") as f:
        if modo == "a":
            f.write("\n\n")
        f.write("\n".join(lineas) + "\n")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-n", type=int, default=None, help="cantidad de estudiantes (por defecto 35)")
    p.add_argument("--regenerar", action="store_true", help="códigos nuevos también para los que ya existen")
    args = p.parse_args(argv)

    ajustes = config.Ajustes()
    n = args.n or ajustes.n_estudiantes
    codigos = generar(ajustes, n, args.regenerar)
    if not codigos:
        print("Todos los estudiantes ya tienen código. Usá --regenerar para cambiarlos.")
        return
    escribir_hoja(ajustes, codigos)
    print(f"{len(codigos)} códigos guardados en {ajustes.db} (solo el hash).")
    print(f"Hoja para imprimir: {ajustes.datos / 'codigos.txt'}")


if __name__ == "__main__":
    main()
