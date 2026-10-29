# Tutor de Ecuaciones Diferenciales · Hugging Face Spaces (Docker) o cualquier host.
# Secretos: ANTHROPIC_API_KEY (obligatorio), DOCENTE_KEY, CODIGOS_SECRETO.
# Modo demostración: solo la variable TUTOR_DEMO=1, sin secretos. El server arranca
# con el tutor guionado y, si la base de /data está vacía, siembra la base demo.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TUTOR_DATOS=/data

# Hugging Face Spaces corre el contenedor con el usuario 1000.
RUN useradd --create-home --uid 1000 tutor \
    && mkdir -p /data && chown tutor:tutor /data

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia todo el contexto (lo que no va está en .dockerignore): así la imagen se
# arma aunque tutor/ todavía no exista y el server use el prompt placeholder.
COPY --chown=tutor:tutor . .

USER tutor
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
