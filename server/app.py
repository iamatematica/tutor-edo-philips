"""Servidor del tutor: FastAPI + SQLite.

Rutas:
- POST /api/login      {id, codigo}           → {token, id}   (abre una sesión)
- POST /api/logout
- POST /api/mensaje    {texto, pista}          → {respuesta, etiqueta_pista, limite_alcanzado}
- GET  /api/historial                          → {mensajes, etiqueta_pista}
- GET  /api/salud
- /                    front estático de web/

Correr local: uvicorn server.app:app --reload
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import acceso, config
from .claude import ClienteClaude, ErrorTutor, Responder
from .db import BaseDatos, ahora
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
TEXTO_LIMITE = (
    "Por hoy llegamos al máximo de mensajes. Buen trabajo: mañana seguimos desde donde quedaste. "
    "Mientras tanto, probá escribir en el papel el paso que venías haciendo."
)


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


def secreto_de_sesion(ajustes: config.Ajustes) -> str:
    """SESION_SECRETO, o uno generado una vez y guardado en datos/ (fuera del repo)."""
    if ajustes.sesion_secreto:
        return ajustes.sesion_secreto
    ruta = ajustes.datos / "secreto_sesion"
    if ruta.is_file():
        return ruta.read_text(encoding="utf-8").strip()
    secreto = acceso.nuevo_secreto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(secreto, encoding="utf-8")
    os.chmod(ruta, 0o600)
    return secreto


def etiqueta_pista(bd: BaseDatos, est_id: str) -> str:
    """'Pista' al empezar un ejercicio; 'Otra pista' si ya se dio alguna."""
    ultimo = bd.ultimo_del_tutor(est_id)
    meta = json.loads(ultimo["meta_json"]) if ultimo and ultimo["meta_json"] else {}
    if (meta.get("escalon") or 0) >= 1 and meta.get("estado") != "resuelto_por_estudiante":
        return "Otra pista"
    return "Pista"


def inicio_del_dia(zona: ZoneInfo, cuando: datetime) -> datetime:
    """Las 0:00 del día en curso en la zona dada (Buenos Aires)."""
    local = cuando.astimezone(zona)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


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
    secreto = secreto_de_sesion(ajustes)
    zona = ZoneInfo(config.ZONA_HORARIA)

    app = FastAPI(title="Tutor de Ecuaciones Diferenciales", docs_url=None, redoc_url=None)
    app.state.ajustes = ajustes
    app.state.bd = bd
    app.state.system_prompt = system_prompt
    app.state.prompt_placeholder = es_placeholder
    app.state.responder = responder
    # Reloj del server; los tests lo reemplazan para simular el paso del tiempo.
    app.state.reloj = ahora

    candados: dict[str, threading.Lock] = {}
    candados_guardia = threading.Lock()
    fallos_login: dict[str, tuple[int, float]] = {}

    def candado(est_id: str) -> threading.Lock:
        with candados_guardia:
            return candados.setdefault(est_id, threading.Lock())

    def estudiante_actual(request: Request, authorization: str = Header(default="")) -> str:
        esquema, _, token = authorization.partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise HTTPException(401, "Iniciá sesión para seguir.")
        momento = int(request.app.state.reloj().timestamp())
        est_id = acceso.leer_token(secreto, token.strip(), bd.codigo_hash, momento)
        if not est_id:
            raise HTTPException(401, "Tu ingreso venció. Volvé a entrar.")
        return est_id

    @app.get("/api/salud")
    def salud():
        return {"ok": True}

    @app.post("/api/login")
    def login(datos: Login, request: Request):
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
        momento = request.app.state.reloj()
        bd.abrir_sesion(est_id, acceso.dispositivo(request.headers.get("user-agent")), momento)
        expira = int(momento.timestamp()) + config.DURACION_TOKEN_HORAS * 3600
        return {"token": acceso.nuevo_token(secreto, est_id, guardado, expira), "id": est_id}

    @app.post("/api/logout")
    def logout():
        # El token no se guarda en el server: salir es que el teléfono lo olvide.
        return {"ok": True}

    @app.get("/api/historial")
    def historial(est_id: str = Depends(estudiante_actual)):
        filas = bd.mensajes(est_id)
        return {
            "id": est_id,
            "mensajes": [
                {
                    "rol": f["rol"],
                    "texto": f["texto"],
                    "pista": f["rol"] == "user" and f["texto"] == TEXTO_PISTA,
                    "creado": f["creado"],
                }
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
            momento = request.app.state.reloj()
            # Límite diario: al alcanzarlo no se llama a la API ni se guarda nada.
            if bd.turnos_desde(est_id, inicio_del_dia(zona, momento)) >= ajustes.limite_turnos_dia:
                return {"respuesta": TEXTO_LIMITE, "etiqueta_pista": etiqueta_pista(bd, est_id),
                        "limite_alcanzado": True}

            sesion = bd.sesion_activa(est_id, config.MINUTOS_SESION, momento)
            if sesion is None:
                # Volvió después de 20 minutos sin mensajes, con el ingreso todavía válido.
                id_sesion = bd.abrir_sesion(est_id, acceso.dispositivo(request.headers.get("user-agent")), momento)
            else:
                id_sesion = sesion["id"]

            # Memoria acotada: solo los últimos turnos de esta sesión.
            previos = bd.ultimos_de_sesion(id_sesion, 2 * config.MAX_TURNOS_CONTEXTO)
            conversacion = contexto_para_claude(previos) + [{"role": "user", "content": texto}]
            try:
                crudo, modelo = request.app.state.responder(request.app.state.system_prompt, conversacion)
            except ErrorTutor as e:
                raise HTTPException(503, MENSAJES_ERROR.get(str(e), MENSAJE_ERROR_GENERICO)) from e

            tutor = extraer(crudo)
            if not tutor["texto"]:
                log.warning("Respuesta vacía del tutor para %s", est_id)
                raise HTTPException(502, MENSAJE_ERROR_GENERICO)
            if tutor["meta_valido"]:
                meta_json = json.dumps(tutor["meta"], ensure_ascii=False)
            else:
                meta_json = None
                log.warning("Meta ausente o inválido para %s (%s): %r", est_id, modelo, tutor["meta_json"])
            bd.guardar_turno(id_sesion, est_id, texto, tutor["texto"], meta_json, request.app.state.reloj())
        finally:
            lock.release()

        return {"respuesta": tutor["texto"], "etiqueta_pista": etiqueta_pista(bd, est_id), "limite_alcanzado": False}

    if ajustes.web.is_dir():
        app.mount("/", StaticFiles(directory=ajustes.web, html=True), name="web")
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = crear_app()
