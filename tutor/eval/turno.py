"""Conducir una conversación de evaluación turno a turno con un tutor externo
(cuando no hay ANTHROPIC_API_KEY, o para probar otro modelo u otra interfaz).

    python tutor/eval/turno.py EST-SIM-03 iniciar --backend agente --modelo <nombre>
        → crea transcripciones/EST-SIM-03.json e imprime el primer mensaje del estudiante
    python tutor/eval/turno.py EST-SIM-03 responder < respuesta_del_tutor.txt
        → guarda la respuesta del tutor (entrada estándar) e imprime el mensaje siguiente, o FIN

El guion de cada estudiante está en estudiantes.yaml; quien hace de tutor no tiene que leerlo.
Después, `python tutor/eval/correr.py --backend grabado` evalúa las transcripciones.
"""

from __future__ import annotations

import argparse
import json
import sys

from correr import cargar_estudiantes, guardar_transcripcion, nueva_transcripcion, ruta_transcripcion


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("estudiante")
    ap.add_argument("accion", choices=["iniciar", "responder"])
    ap.add_argument("--backend", default="externo")
    ap.add_argument("--modelo", default="desconocido")
    args = ap.parse_args()

    est = next((e for e in cargar_estudiantes() if e["id"] == args.estudiante), None)
    if est is None:
        sys.exit(f"No existe {args.estudiante}")
    mensajes = [m["texto"] for m in est["mensajes"]]

    if args.accion == "iniciar":
        guardar_transcripcion(nueva_transcripcion(est["id"], args.backend, args.modelo))
        print(f"ESTUDIANTE: {mensajes[0]}")
        return

    ruta = ruta_transcripcion(est["id"])
    t = json.loads(ruta.read_text(encoding="utf-8"))
    n = len(t["turnos"])
    if n >= len(mensajes):
        print("FIN")
        return
    respuesta = sys.stdin.read().strip()
    if not respuesta:
        sys.exit("La respuesta del tutor llegó vacía")
    t["turnos"].append({"estudiante": mensajes[n], "tutor": respuesta})
    guardar_transcripcion(t)
    print(f"ESTUDIANTE: {mensajes[n + 1]}" if n + 1 < len(mensajes) else "FIN")


if __name__ == "__main__":
    main()
