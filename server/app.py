"""Servidor del tutor: FastAPI + SQLite.

Rutas:
- POST /api/login      {id, codigo}           → {token, id}
- POST /api/logout
- POST /api/mensaje    {texto, pista}          → {respuesta, etiqueta_pista}
- GET  /api/historial                          → {mensajes, etiqueta_pista}
- GET  /api/salud
- /                    front estático de web/

Correr local: uvicorn server.app:app --reload
"""
from __future__ import annotations

import logging
import threading
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import acceso, config
from .claude import ClienteClaude, ErrorTutor, Responder
from .db import BaseDatos
from .meta import extraer

log = logging.getLogger("tutor")

TEXTO_PISTA = "Pista"
MAX_FALLOS_LOGIN = 5
BLOQUEO_LOGIN_SEG = 300

MENSAJES_ERROR = {
    "limite": "El tutor está muy pedido en este momento. Probá de nuevo en un minuto.",
    "autenticacion": "El tutor no está disponible ahora. Avisale a tu profe.",
    "configuracion": "El tutor no está disponible ahora. Avisale a tu profe.",
}
MENSAJE_ERROR_GENERICO = "No pude responder. Probá de nuevo en un momento."


def cargar_system_prompt(ajustes: config.Ajustes) -> tuple[str, bool]:
    """Lee tutor/system_prompt.md; si todavía no existe, usa el placeholder del server."""
    if ajustes.system_prompt.is_file():
        return ajustes.system_prompt.read_text(encoding="utf-8"), False
    log.warning("No existe %s: se usa el prompt placeholder.", ajustes.system_prompt)
    return ajustes.placeholder.read_text(encoding="utf-8"), True


def sembrar_estudiantes(bd: BaseDatos, secreto: str, n: int) -> None:
    """Con CODIGOS_SECRETO definido, la tabla de estudiantes se arma desde el secreto."""
    for i in range(1, n + 1):
        est = acceso.id_estudiante(i)
        guardado = bd.codigo_hash(est)
        codigo = acceso.codigo_derivado(secreto, est)
        if guardado is None or not acceso.verificar_codigo(codigo, guardado):
            bd.guardar_estudiante(est, acceso.hash_codigo(codigo))


class Login(BaseModel):
    id: str = Field(max_length=20)
    codigo: str = Field(max_length=40)


class Mensaje(BaseModel):
    texto: str = Field(default="", max_length=config.MAX_LARGO_MENSAJE)
    pista: bool = False


def etiqueta_pista(bd: BaseDatos, est_id: str) -> str:
    """'Pista' al empezar un ejercicio; 'Otra pista' si ya se dio alguna."""
    ultimo = bd.ultimo_del_tutor(est_id)
    if ultimo and (ultimo["escalon"] or 0) >= 1 and ultimo["estado"] != "resuelto_por_estudiante":
        return "Otra pista"
    return "Pista"


def contexto_para_claude(filas) -> list[dict]:
    mensajes = [{"role": f["rol"], "content": f["texto"]} for f in filas]
    # La API exige que la conversación empiece con el estudiante.
    while mensajes and mensajes[0]["role"] != "user":
        mensajes.pop(0)
    return mensajes


def crear_app(ajustes: config.Ajustes | None = None, responder: Responder | None = None) -> FastAPI:
    ajustes = ajustes or config.Ajustes()
    bd = BaseDatos(ajustes.db)
    if ajustes.codigos_secreto:
        sembrar_estudiantes(bd, ajustes.codigos_secreto, ajustes.n_estudiantes)
    system_prompt, es_placeholder = cargar_system_prompt(ajustes)
    responder = responder or ClienteClaude(ajustes.modelo, ajustes.esfuerzo, ajustes.max_tokens)

    app = FastAPI(title="Tutor de Ecuaciones Diferenciales", docs_url=None, redoc_url=None)
    app.state.ajustes = ajustes
    app.state.bd = bd
    app.state.system_prompt = system_prompt
    app.state.prompt_placeholder = es_placeholder
    app.state.responder = responder

    candados: dict[str, threading.Lock] = {}
    candados_guardia = threading.Lock()
    fallos_login: dict[str, tuple[int, float]] = {}

    def candado(est_id: str) -> threading.Lock:
        with candados_guardia:
            return candados.setdefault(est_id, threading.Lock())

    def estudiante_actual(authorization: str = Header(default="")) -> str:
        esquema, _, token = authorization.partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise HTTPException(401, "Iniciá sesión para seguir.")
        est_id = bd.estudiante_de_sesion(acceso.hash_token(token.strip()))
        if not est_id:
            raise HTTPException(401, "Tu sesión venció. Volvé a entrar.")
        return est_id

    @app.get("/api/salud")
    def salud():
        return {"ok": True}

    @app.post("/api/login")
    def login(datos: Login):
        est_id = acceso.normalizar_id(datos.id)
        if not est_id:
            raise HTTPException(400, "El identificador tiene la forma EST-07.")
        fallos, hasta = fallos_login.get(est_id, (0, 0.0))
        if hasta > time.monotonic():
            raise HTTPException(429, "Demasiados intentos. Esperá unos minutos y probá de nuevo.")
        guardado = bd.codigo_hash(est_id)
        if not guardado or not acceso.verificar_codigo(datos.codigo, guardado):
            fallos += 1
            bloqueo = time.monotonic() + BLOQUEO_LOGIN_SEG if fallos >= MAX_FALLOS_LOGIN else 0.0
            fallos_login[est_id] = (0 if bloqueo else fallos, bloqueo)
            raise HTTPException(401, "El identificador o el código no coinciden.")
        fallos_login.pop(est_id, None)
        token = acceso.nuevo_token()
        bd.crear_sesion(acceso.hash_token(token), est_id, config.DURACION_SESION_HORAS)
        return {"token": token, "id": est_id}

    @app.post("/api/logout")
    def logout(authorization: str = Header(default="")):
        _, _, token = authorization.partition(" ")
        if token:
            bd.cerrar_sesion(acceso.hash_token(token.strip()))
        return {"ok": True}

    @app.get("/api/historial")
    def historial(est_id: str = Depends(estudiante_actual)):
        filas = bd.mensajes(est_id)
        return {
            "id": est_id,
            "mensajes": [
                {"rol": f["rol"], "texto": f["texto"], "pista": bool(f["es_pista"]), "creado": f["creado"]}
                for f in filas
            ],
            "etiqueta_pista": etiqueta_pista(bd, est_id),
        }

    @app.post("/api/mensaje")
    def mensaje(datos: Mensaje, request: Request, est_id: str = Depends(estudiante_actual)):
        texto = TEXTO_PISTA if datos.pista else datos.texto.strip()
        if not texto:
            raise HTTPException(422, "Escribí algo antes de enviar.")

        lock = candado(est_id)
        if not lock.acquire(blocking=False):
            raise HTTPException(429, "Esperá la respuesta anterior.")
        try:
            previos = bd.mensajes(est_id, limite=config.MAX_MENSAJES_CONTEXTO)
            conversacion = contexto_para_claude(previos) + [{"role": "user", "content": texto}]
            try:
                crudo, modelo = request.app.state.responder(request.app.state.system_prompt, conversacion)
            except ErrorTutor as e:
                raise HTTPException(503, MENSAJES_ERROR.get(str(e), MENSAJE_ERROR_GENERICO)) from e

            tutor = extraer(crudo)
            if not tutor["texto"]:
                log.warning("Respuesta vacía del tutor para %s", est_id)
                raise HTTPException(502, MENSAJE_ERROR_GENERICO)
            if not tutor["meta_valido"]:
                log.warning("Meta ausente o inválido para %s: %r", est_id, tutor["meta_json"])
            tutor["texto_crudo"] = crudo
            tutor["modelo"] = modelo
            bd.guardar_turno(est_id, texto, datos.pista, tutor)
        finally:
            lock.release()

        return {"respuesta": tutor["texto"], "etiqueta_pista": etiqueta_pista(bd, est_id)}

    if ajustes.web.is_dir():
        app.mount("/", StaticFiles(directory=ajustes.web, html=True), name="web")
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = crear_app()
