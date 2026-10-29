---
title: Tutor de Ecuaciones Diferenciales
emoji: 📐
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.30.0
python_version: "3.11"
app_file: app.py
app_port: 7860
pinned: false
---

# Tutor de Ecuaciones Diferenciales · Escuela Técnica Philips · 5.º año

Tutor conversacional para la unidad Ecuaciones Diferenciales de primer orden. Orienta con pistas, no califica y no da la respuesta final. El contrato completo del proyecto está en [`CLAUDE.md`](CLAUDE.md); las decisiones y desvíos, en [`NOTAS.md`](NOTAS.md).

> El bloque de arriba (entre `---`) es la configuración que lee Hugging Face Spaces. En GitHub se ve como una tabla. Está preparado para un Space **Gradio** (gratuito): el Space corre `app.py`, que monta la app del tutor. Para un Space Docker, cambiar `sdk: gradio` por `sdk: docker` y borrar `sdk_version`, `python_version` y `app_file`.

## Qué hay

| Carpeta | Qué es |
|---|---|
| `server/` | FastAPI + SQLite: login seudonimizado, chat, extracción del metadato `<meta>` de cada respuesta |
| `web/` | Front estático (HTML + CSS + JS, sin build): login `EST-NN` + código, chat con KaTeX y botón **Pista** |
| `panel/` | Panel docente estático (`/panel`): métricas del curso y por estudiante, conversaciones completas, exportación CSV |
| `tutor/` | System prompt, banco de ejercicios y evaluación (Fase 1) |
| `app.py` | Arranque para un Space Gradio: monta la app del tutor y sirve en el puerto 7860 |
| `Dockerfile` | Imagen para un Space Docker (puerto 7860) o cualquier host |

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
| `ANTHROPIC_API_KEY` | Clave de la API de Claude (**obligatoria**, salvo en modo demostración; nunca en el repo) | — |
| `CODIGOS_SECRETO` | Si está definida, los códigos se derivan de este secreto y el server arma solo la tabla de estudiantes al arrancar | sin definir: códigos aleatorios con `generar_codigos` |
| `TUTOR_DATOS` | Carpeta de la base `tutor.db` y de `codigos.txt` | `datos/` (en Docker, `/data`) |
| `TUTOR_N_ESTUDIANTES` | Cantidad de estudiantes | `35` |
| `TUTOR_LIMITE_TURNOS_DIA` | Turnos por alumno por día; se reinicia a las 0:00 de Buenos Aires | `80` |
| `SESION_SECRETO` | Firma de los ingresos. Si falta, se genera uno y se guarda en `datos/secreto_sesion` | generado |
| `TUTOR_MODELO` | Modelo de Claude | `claude-sonnet-5-5` |
| `TUTOR_ESFUERZO` | Esfuerzo del modelo (`low`, `medium`, `high`) | `low` |
| `TUTOR_SYSTEM_PROMPT` | Ruta del system prompt | `tutor/system_prompt.md` |
| `DOCENTE_KEY` | Clave del panel docente. Sin ella, el panel queda deshabilitado | — |
| `TUTOR_COSTO_MEDIO_TURNO` | Costo medio por turno en US$, para el indicador de costo del panel | `0.006` |
| `TUTOR_DEMO` | `1`: modo demostración (tutor guionado sin API, base demo, clave del panel `demo`). Ver [Modo demostración](#modo-demostración) | sin definir |

El system prompt se lee de `tutor/system_prompt.md` en cada arranque. Si todavía no existe, el server usa `server/system_prompt_placeholder.md` y lo avisa en el log.

Otros parámetros fijos (memoria de 12 turnos, sesión cerrada a los 20 minutos sin mensajes, costo medio por turno para el panel) están en `server/config.py`.

## Costo y tope de gasto

- Cada llamada a la API lleva el system prompt (cacheado) y solo los **últimos 12 turnos** de la sesión, así que el costo por turno no crece en sesiones largas.
- Cada alumno tiene **80 turnos por día**. Al llegar al límite, el tutor contesta que siguen mañana y el server no llama a la API. El contador vuelve a cero a las 0:00 de Buenos Aires.
- **Tope mensual en la consola de la API: 200 US$ para el piloto.** Se fija en la consola ([platform.claude.com](https://platform.claude.com)), en los límites de gasto de la organización o del workspace de la clave. El server no lo controla: es la red de seguridad por si algo se dispara. Referencia: 35 alumnos × 3 sesiones por semana × 80 turnos × 4 semanas ≈ 200 US$ con Sonnet 5.5 como techo.
- `COSTO_MEDIO_TURNO_USD` en `server/config.py` (0,006 US$ al arrancar) alimenta el indicador de costo del panel docente. Conviene recalibrarlo con el gasto real de la primera semana.

## Modo demostración

Para mostrar el sistema a la institución **sin clave de la API y sin costo**. Con `TUTOR_DEMO=1`:

- el server arranca sin `ANTHROPIC_API_KEY` y la llamada a la API se reemplaza por un **tutor guionado** (`server/demo.py`), que no es una IA: propone ejercicios del banco (`tutor/banco/*.yaml`), da sus pistas en orden (una por pedido, con el botón **Pista** o pidiendo ayuda), después de la cuarta no avanza y pide el intento, contesta los intentos con un comentario genérico que no da la solución, y si el estudiante escribe una ecuación que no está en el banco le propone una del banco. Cada respuesta lleva su `<meta>`, como el tutor real;
- el chat y el panel muestran el cartel **«Modo demostración · respuestas guionadas, sin IA»**;
- si la base está vacía, se siembra sola con los 35 estudiantes y los datos inventados que se usaron para las capturas del panel (107 sesiones, 509 turnos, del 2 al 18 de noviembre de 2026);
- la clave del panel es `demo`, salvo que se defina `DOCENTE_KEY`.

Sin `TUTOR_DEMO`, nada de esto cambia el comportamiento del tutor.

**Los datos son inventados y los códigos de la demo son siempre los mismos** (salen de un secreto fijo, salvo que se defina `CODIGOS_SECRETO`): esta base es solo para mostrar, nunca para el curso.

### Local, en tres comandos

```bash
pip install -r requirements.txt
```

```bash
python -m server.sembrar_demo
```

```bash
TUTOR_DEMO=1 uvicorn server.app:app
```

El segundo comando crea `datos/tutor.db` e imprime los 35 códigos. Abrir <http://localhost:8000>: para chatear con el historial vacío, entrar como `EST-13` o `EST-29` (los dos únicos que no tienen sesiones sembradas); el resto ya trae conversaciones inventadas. El panel está en <http://localhost:8000/panel>, con la clave `demo`.

- `python -m server.sembrar_demo --codigos` imprime los códigos sin tocar la base.
- Sobre una base con datos, el comando no hace nada y avisa: para empezar de cero, borrar `datos/tutor.db` (si es de prueba) o usar otra carpeta con `TUTOR_DATOS=otra-carpeta`.
- Para probarlo igual que en el Space: `TUTOR_DEMO=1 python app.py` y abrir <http://localhost:7860>.

### Publicarlo en un Space de Hugging Face gratuito (SDK Gradio)

En la cuenta del docente los Spaces Docker son pagos y los Gradio son gratuitos, así que la demo va en un Space **Gradio**. El Space corre `python app.py`. Ese archivo monta la app FastAPI del tutor en `/`, le agrega una página Gradio mínima en `/gradio` (solo para que el SDK la acepte) y sirve todo con uvicorn en el puerto 7860. El bloque de configuración del principio de este README ya dice `sdk: gradio`, `app_file: app.py` y `app_port: 7860`.

1. **Crear el Space.** Con la sesión iniciada en <https://huggingface.co>, ir a <https://huggingface.co/new-space> y completar:
   - *Space name*: por ejemplo `tutor-edo-demo`.
   - *Select the Space SDK*: **Gradio**, plantilla *Blank*.
   - *Space hardware*: **CPU basic · Free**.
   - *Public* o *Private* (si es privado, solo entran quienes tengan acceso a la cuenta; para mostrarlo a la institución sin cuentas, *Public*).

   Apretar *Create Space*.
2. **Definir la variable.** En el Space: *Settings → Variables and secrets → New variable*. Nombre `TUTOR_DEMO`, valor `1`. Es una **variable**, no un secreto: la demo no lleva ninguna clave. No cargar `ANTHROPIC_API_KEY`.
3. **Crear un token.** En <https://huggingface.co/settings/tokens>, *Create new token* con permiso de escritura (*Write*). Copiarlo.
4. **Subir el repositorio** desde la carpeta del proyecto, en la computadora:

   ```bash
   pip install -U huggingface_hub
   ```

   ```bash
   hf auth login
   ```

   (pegar el token cuando lo pida) y, cambiando `USUARIO` por el nombre de la cuenta:

   ```bash
   hf upload USUARIO/tutor-edo-demo . . --repo-type space --exclude "datos/*" "docs/*" ".git/*" ".claude/*" ".venv/*" "**/__pycache__/*"
   ```

   Se excluyen `datos/` (la base local y los códigos), las capturas de `docs/` (el Space rechaza imágenes subidas fuera de su almacenamiento de archivos grandes y no hacen falta) y las carpetas de trabajo. Para actualizar el Space después de un cambio, repetir el mismo `hf upload`.
5. **Esperar el arranque.** En la pestaña *Logs* del Space se ve la instalación y, al final, `MODO DEMOSTRACIÓN` y la lista de los 35 códigos. Cuando el estado pasa a *Running*, abrir el Space: el chat está en `https://USUARIO-tutor-edo-demo.hf.space` y el panel en `https://USUARIO-tutor-edo-demo.hf.space/panel` (clave `demo`). Los códigos también salen en la computadora con `python -m server.sembrar_demo --codigos`.

En el plan gratuito el disco del Space no es persistente y el Space se duerme tras un tiempo sin visitas: al despertar o reiniciarse arranca con la base vacía y la vuelve a sembrar (mismos códigos y mismos datos; se pierde lo que se haya chateado en la demo). Para la demo eso alcanza; para el curso real va el despliegue de abajo, con almacenamiento persistente y la clave de la API.

## Despliegue en Hugging Face Spaces

Para el curso real, con la API de Claude.

1. Crear el Space y subir este repositorio. Con un Space **Gradio** (como la demo) el bloque de configuración sirve tal cual; con uno **Docker**, cambiarlo como dice la nota del principio.
2. En *Settings → Variables and secrets*, cargar como **secretos** `ANTHROPIC_API_KEY`, `CODIGOS_SECRETO` y, para la Fase 3, `DOCENTE_KEY`.
3. En *Settings → Persistent storage*, activar el almacenamiento persistente: se monta en `/data`, que es donde la imagen Docker guarda la base; en un Space Gradio, agregar además la variable `TUTOR_DATOS=/data`. **Sin almacenamiento persistente, las conversaciones se pierden cada vez que el Space se reinicia.**
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
| `POST /api/login` | `{"id": "EST-07", "codigo": "ABC-234"}` | `{"token", "id"}` (abre una sesión) |
| `POST /api/logout` | — | `{"ok": true}` |
| `POST /api/mensaje` | `{"texto": "...", "pista": false}` | `{"respuesta", "etiqueta_pista", "limite_alcanzado"}` |
| `GET /api/historial` | — | `{"id", "mensajes": [{"rol", "texto", "pista", "creado"}], "etiqueta_pista"}` |
| `GET /api/salud` | — | `{"ok": true}`; con `TUTOR_DEMO=1`, además `"demo": true` y `"clave_demo"` (si la clave del panel es `demo`) |

| `GET /api/metricas` | — | métricas del curso, por estudiante, por ejercicio, errores y costo |
| `GET /api/metricas/conversacion/EST-07` | — | todas las sesiones del estudiante con sus mensajes y el `<meta>` de cada respuesta |
| `GET /api/metricas/csv/{tabla}` | — | CSV de `estudiantes`, `curso`, `semanas`, `sesiones`, `ejercicios`, `errores`, `costo` o `mensajes` |

Las rutas `/api/metricas…` piden la clave del docente en `X-Docente-Key` (o `Authorization: Bearer <clave>`); tras 10 claves incorrectas seguidas se bloquean 5 minutos.

`/api/mensaje` y `/api/historial` piden `Authorization: Bearer <token>`. El token va firmado y no se guarda en el server; vence a la semana o cuando se regenera el código del estudiante. El botón **Pista** manda `{"pista": true}`, y el server lo registra como el mensaje `Pista` del estudiante. El metadato `<meta>` de cada respuesta se guarda validado en `mensajes.meta_json` (se consulta con `json_extract`) y nunca llega al front.

## Panel docente

Abrir <http://localhost:8000/panel> (en el Space, `https://<space>/panel`) e ingresar la clave `DOCENTE_KEY`. La clave queda guardada solo mientras dure la pestaña.

```bash
DOCENTE_KEY='una-clave-larga' ANTHROPIC_API_KEY=sk-ant-... uvicorn server.app:app --reload
```

| Pestaña | Qué muestra |
|---|---|
| Curso | estudiantes activos, ingresos, minutos conectados, turnos y turnos por sesión, ejercicios abordados y resueltos, proporción de orientación, escalón promedio; costo estimado del día y del mes frente al tope de 200 US$; ingresos por semana; qué pide el estudiante; dispositivo |
| Estudiantes | las mismas métricas por estudiante (ordenables; los 35 aparecen aunque no hayan entrado) y la tabla de ingresos por semana |
| Ejercicios y errores | ejercicios más trabados (abordados, trabados, resueltos, escalón promedio) y errores por código |
| Conversaciones | la conversación completa de un estudiante, sesión por sesión, con el metadato de cada respuesta del tutor |
| Exportar | todo lo anterior en CSV (separador `;`, coma decimal, se abre directo en Excel) |

Cómo se calcula cada número está al principio de `server/metricas.py`.

## Base de datos

`datos/tutor.db`, con las tablas que fija `CLAUDE.md`:

- `estudiantes(id, codigo_hash)`
- `sesiones(id, estudiante, inicio, ultima_actividad, dispositivo)`: se abre en el login; tras 20 minutos sin mensajes, el mensaje siguiente abre otra. `dispositivo` es `celular` o `computadora` según el navegador.
- `mensajes(id, sesion, estudiante, rol, texto, meta_json, creado)`

## Privacidad

- Solo identificadores `EST-01 … EST-35` y el hash de cada código. Ningún nombre, correo ni dirección IP.
- `datos/`, `.env` y `codigos*.txt` están en `.gitignore`.
- Todas las conversaciones quedan registradas para revisión docente.
