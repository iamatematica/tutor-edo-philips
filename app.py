"""Arranque para un Space de Hugging Face con SDK Gradio (los Spaces Gradio son gratuitos).

El Space corre `python app.py`. Esto monta la app FastAPI del tutor (server/app.py)
tal cual en `/`, le agrega una página Gradio mínima en `/gradio` (solo para que el
SDK la acepte) y sirve todo con uvicorn en el puerto 7860.

Con TUTOR_DEMO=1 (variable del Space, no secreto) el server arranca sin
ANTHROPIC_API_KEY, con el tutor guionado, y siembra la base demo si está vacía.

Local, igual que en el Space:  TUTOR_DEMO=1 python app.py
"""
from __future__ import annotations

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from server.app import app as tutor  # noqa: E402  (al importarse arma la app y, en demo, siembra la base)

with gr.Blocks(title="Tutor de Ecuaciones Diferenciales") as minimo:
    gr.Markdown(
        "### Tutor de Ecuaciones Diferenciales · Escuela Philips\n\n"
        "El chat de los estudiantes está en [la página principal](/) y el panel docente en [/panel](/panel/)."
    )

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app = gr.mount_gradio_app(app, minimo, path="/gradio")
# El tutor va último: su montaje en "/" atiende todo lo que no sea /gradio.
app.mount("/", tutor)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
