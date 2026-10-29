"""Rutas del panel docente (Fase 3).

- GET /api/metricas                        → todas las métricas del curso y por estudiante
- GET /api/metricas/conversacion/{EST-NN}  → la conversación completa, sesión por sesión, con el <meta>
- GET /api/metricas/csv/{tabla}            → la tabla en CSV (separador ;, coma decimal, UTF-8 con BOM)

Todas piden la clave del docente (variable de entorno DOCENTE_KEY) en el encabezado
`X-Docente-Key` o como `Authorization: Bearer <clave>`. Sin DOCENTE_KEY definida, el
panel queda deshabilitado (503). El HTML del panel (/panel) es estático y no trae datos.
"""
from __future__ import annotations

import csv
import hmac
import io
import threading
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response

from . import acceso, metricas

MAX_FALLOS = 10
BLOQUEO_SEG = 300


def crear_router() -> APIRouter:
    router = APIRouter(prefix="/api/metricas")
    # Fallos de clave para todo el panel: tras 10 seguidos, 5 minutos de bloqueo.
    estado = {"fallos": 0, "hasta": 0.0}
    guardia = threading.Lock()

    def docente(request: Request, x_docente_key: str = Header(default=""), authorization: str = Header(default="")):
        clave = request.app.state.ajustes.docente_key
        if not clave:
            raise HTTPException(503, "El panel está deshabilitado: falta definir DOCENTE_KEY en el servidor.")
        esquema, _, token = authorization.partition(" ")
        dada = x_docente_key or (token.strip() if esquema.lower() == "bearer" else "")
        with guardia:
            if estado["hasta"] > time.monotonic():
                raise HTTPException(429, "Demasiados intentos con una clave incorrecta. Esperá unos minutos.")
            if not dada or not hmac.compare_digest(dada.encode(), clave.encode()):
                estado["fallos"] += 1
                if estado["fallos"] >= MAX_FALLOS:
                    estado["fallos"], estado["hasta"] = 0, time.monotonic() + BLOQUEO_SEG
                raise HTTPException(401, "Clave de docente incorrecta.")
            estado["fallos"] = 0

    def parametros(request: Request) -> dict:
        ajustes = request.app.state.ajustes
        return {"costo_turno": ajustes.costo_medio_turno, "tope_mensual": ajustes.tope_mensual}

    @router.get("", dependencies=[Depends(docente)])
    def todas(request: Request):
        return metricas.calcular(request.app.state.bd, request.app.state.reloj(), **parametros(request))

    @router.get("/conversacion/{est}", dependencies=[Depends(docente)])
    def conversacion(est: str, request: Request):
        est_id = acceso.normalizar_id(est)
        if not est_id or request.app.state.bd.codigo_hash(est_id) is None:
            raise HTTPException(404, "No existe ese estudiante.")
        return metricas.conversacion(request.app.state.bd, est_id)

    @router.get("/csv/{tabla}", dependencies=[Depends(docente)])
    def exportar(tabla: str, request: Request):
        tablas = metricas.tablas_csv(request.app.state.bd, request.app.state.reloj(), **parametros(request))
        if tabla not in tablas:
            raise HTTPException(404, "Tablas disponibles: " + ", ".join(tablas))
        encabezados, filas = tablas[tabla]
        salida = io.StringIO()
        escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
        escritor.writerow(encabezados)
        escritor.writerows(filas)
        fecha = request.app.state.reloj().strftime("%Y%m%d")
        return Response(
            "﻿" + salida.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="tutor-{tabla}-{fecha}.csv"',
                     "Cache-Control": "no-store"},
        )

    return router
