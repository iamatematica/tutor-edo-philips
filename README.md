---
title: Tutor de Ecuaciones Diferenciales
emoji: 📐
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Tutor de Ecuaciones Diferenciales · Escuela Técnica Philips · 5.º año

Tutor conversacional para la unidad Ecuaciones Diferenciales de primer orden. Orienta con pistas, no califica y no da la respuesta final. El contrato completo del proyecto está en [`CLAUDE.md`](CLAUDE.md); las decisiones y desvíos, en [`NOTAS.md`](NOTAS.md).

> El bloque de arriba (entre `---`) es la configuración que lee Hugging Face Spaces. En GitHub se ve como una tabla; no hace falta tocarlo.

## Qué hay

| Carpeta | Qué es |
|---|---|
| `server/` | FastAPI + SQLite: login seudonimizado, chat, extracción del metadato `<meta>` de cada respuesta |
| `web/` | Front estático (HTML + CSS + JS, sin build): login `EST-NN` + código, chat con KaTeX y botón **Pista** |
| `tutor/` | System prompt, banco de ejercicios y evaluación (Fase 1) |
| `Dockerfile` | Imagen para Hugging Face Spaces (puerto 7860) o cualquier host |

## Arranque local

Requiere Python 3.11 o más nuevo.

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements-dev.txt
```

Generar los códigos de los 35 estudiantes (quedan en `datos/codigos.txt` para imprimir; en la base solo se guarda el hash):

```bash
python -m server.generar_codigos
```

Levantar el server con la clave de la API de Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-... uvicorn server.app:app --reload
```

Abrir <http://localhost:8000> y entrar con un identificador (`EST-07`, o solo `7`) y su código.

### Tests

```bash
pytest server/tests
```

Los tests no llaman a la API: reemplazan al tutor por uno falso.

## Variables de entorno

| Variable | Para qué | Por defecto |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Claude (**obligatoria**, nunca en el repo) | — |
| `CODIGOS_SECRETO` | Si está definida, los códigos se derivan de este secreto y el server arma solo la tabla de estudiantes al arrancar | sin definir: códigos aleatorios con `generar_codigos` |
| `TUTOR_DATOS` | Carpeta de la base `tutor.db` y de `codigos.txt` | `datos/` (en Docker, `/data`) |
| `TUTOR_N_ESTUDIANTES` | Cantidad de estudiantes | `35` |
| `TUTOR_MODELO` | Modelo de Claude | ver `server/config.py` |
| `TUTOR_ESFUERZO` | Esfuerzo del modelo (`low`, `medium`, `high`) | `low` |
| `TUTOR_SYSTEM_PROMPT` | Ruta del system prompt | `tutor/system_prompt.md` |
| `DOCENTE_KEY` | Clave del panel docente (Fase 3) | — |

El system prompt se lee de `tutor/system_prompt.md` en cada arranque. Si todavía no existe, el server usa `server/system_prompt_placeholder.md` y lo avisa en el log.

## Despliegue en Hugging Face Spaces

1. Crear un Space de tipo **Docker** y subir este repositorio (el `README.md` ya trae la configuración).
2. En *Settings → Variables and secrets*, cargar como **secretos** `ANTHROPIC_API_KEY`, `CODIGOS_SECRETO` y, para la Fase 3, `DOCENTE_KEY`.
3. En *Settings → Persistent storage*, activar el almacenamiento persistente: se monta en `/data`, que es donde la imagen guarda la base. **Sin almacenamiento persistente, las conversaciones se pierden cada vez que el Space se reinicia.**
4. En la computadora del docente, con el mismo secreto, generar la hoja de códigos para imprimir:

   ```bash
   CODIGOS_SECRETO='el-mismo-secreto' TUTOR_DATOS=datos-hf python -m server.generar_codigos
   ```

   Los códigos de `datos-hf/codigos.txt` son los mismos que acepta el Space, porque los dos se derivan del secreto.

### Otro host

```bash
docker build -t tutor-edo .
```

```bash
docker run -p 7860:7860 -e ANTHROPIC_API_KEY=sk-ant-... -e CODIGOS_SECRETO=... -v "$PWD/datos:/data" tutor-edo
```

## API

| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /api/login` | `{"id": "EST-07", "codigo": "ABC-234"}` | `{"token", "id"}` |
| `POST /api/logout` | — | `{"ok": true}` |
| `POST /api/mensaje` | `{"texto": "...", "pista": false}` | `{"respuesta", "etiqueta_pista"}` |
| `GET /api/historial` | — | `{"id", "mensajes": [{"rol", "texto", "pista", "creado"}], "etiqueta_pista"}` |
| `GET /api/salud` | — | `{"ok": true}` |

`/api/mensaje` y `/api/historial` piden `Authorization: Bearer <token>`. El botón **Pista** manda `{"pista": true}`, y el server lo registra como el mensaje `Pista` del estudiante. El metadato `<meta>` de cada respuesta se guarda en la base (`mensajes.meta_json`, y sus campos en columnas aparte) y nunca llega al front.

## Privacidad

- Solo identificadores `EST-01 … EST-35` y el hash de cada código. Ningún nombre ni correo.
- `datos/`, `.env` y `codigos*.txt` están en `.gitignore`.
- Todas las conversaciones quedan registradas para revisión docente.
