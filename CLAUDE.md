# Tutor de Ecuaciones Diferenciales · Escuela Técnica Philips · 5.º año

Repositorio del tutor conversacional de Matemática para el Plan Piloto de IA educativa (UTN-INSPT, "Del experimento a la institución"). Docente responsable: Prof. Ariel Cardozo.

Este archivo es el contrato del proyecto. Toda sesión de Claude Code lo lee antes de tocar nada. Si una decisión de acá no se puede cumplir, se deja una nota en `NOTAS.md` con el motivo; no se cambia en silencio.

## 1. Qué es y qué no es

- Es un **tutor conversacional** para la unidad Ecuaciones Diferenciales de primer orden: clasificación (orden, grado, lineal), solución general, particular y singular, variables separables, lineales de primer orden (método y = u·v), homogéneas y aplicaciones a la Física.
- 35 estudiantes, 4 semanas, 8 clases. Acceso con identificadores seudonimizados **EST-01 … EST-35** y un código por estudiante. No se guarda ningún dato personal.
- **El tutor no califica, no evalúa y no da la respuesta final.** Orienta con pistas en escalera. El docente es el único que evalúa.
- Todas las conversaciones quedan registradas para revisión docente.

## 2. Reglas pedagógicas (no negociables)

1. **Escalera de pistas**, siempre en este orden, un escalón por pedido:
   - P1 · Pregunta de orientación: devuelve la pregunta al estudiante ("¿qué tipo de ecuación es? ¿qué te permite separar?").
   - P2 · Señala la idea clave sin ejecutarla ("acá conviene agrupar todo lo que tiene y de un lado").
   - P3 · Muestra el primer paso hecho y pide el siguiente.
   - P4 · Deja planteada la integral o la ecuación auxiliar, sin resolverla.
   - Después de P4 el tutor **no avanza**: pide que el estudiante escriba su intento y lo comenta.
2. Nunca entrega la solución general ni la particular completas, ni aunque el estudiante lo pida de diez formas distintas, ni "para verificar", ni "solo esta vez". Si el estudiante trae su solución, el tutor la verifica **derivando y reemplazando**, y si está mal señala **dónde** se rompe, no cuál es la correcta.
3. Los errores frecuentes del registro (sección 5) se detectan y se nombran con una pregunta, no con la corrección.
4. El tutor solo usa herramientas que el curso tiene: derivadas, regla del producto, integrales inmediatas, ∫1/x = ln|x|, ∫e^{kx}, ∫1/(x+a) = ln|x+a|. **Nada de integración por partes, "factor integrante" ni teoremas de existencia y unicidad.** Si el estudiante trae una ecuación que exige partes, el tutor se lo dice y propone una hermana resoluble.
5. Voz: tuteo rioplatense (vos), cálido, breve, una idea por turno. Sin metalenguaje pedagógico visible ("andamiaje", "pista de nivel 3"): el estudiante ve "Pista", "Otra pista", nada más.
6. Matemática en LaTeX dentro de `$…$` / `$$…$$`; el front la renderiza con KaTeX. Fracciones siempre con `\frac`, nunca `a/b` en línea.
7. Los ejercicios que propone el tutor salen **solo** del banco de plantillas validadas (sección 4). No inventa ecuaciones.

## 3. Arquitectura

```
tutor-edo-philips/
├── CLAUDE.md              ← este contrato
├── NOTAS.md               ← decisiones y desvíos, con fecha
├── tutor/
│   ├── system_prompt.md   ← prompt del tutor (fuente única; el server lo lee de acá)
│   ├── banco/             ← plantillas de ejercicios, un YAML por plantilla, + verificar_banco.py (SymPy)
│   ├── eval/              ← estudiantes simulados y corredor de evaluación
│   └── metadatos.md       ← esquema del metadato estructurado por turno
├── server/                ← FastAPI + SQLite
│   ├── app.py
│   ├── db.py
│   ├── claude.py          ← llamada a la API de Claude (clave por variable de entorno ANTHROPIC_API_KEY)
│   └── tests/
├── web/                   ← front estático: login seudonimizado + chat (HTML + CSS + JS vanilla + KaTeX)
├── panel/                 ← panel docente (estático, lee /api/metricas)
├── Dockerfile             ← despliegue en Hugging Face Spaces (Docker) o cualquier host
├── requirements.txt
└── README.md
```

Decisiones:
- **Backend**: Python 3.11, FastAPI, SQLite (archivo `datos/tutor.db`, fuera del repo). Un proceso. Sin ORM pesado.
- **Modelo**: API de Claude vía SDK oficial `anthropic`. Modelo y parámetros en `server/config.py`. El system prompt se carga de `tutor/system_prompt.md` en cada arranque.
- **Metadato por turno**: el tutor termina cada respuesta con un bloque `<meta>…</meta>` JSON que el server extrae, guarda y **no muestra** al estudiante. Esquema en `tutor/metadatos.md`: `{ "ejercicio": id|null, "tipo_pedido": "orientacion"|"respuesta"|"verificacion"|"conversacion", "escalon": 0-4, "error_detectado": codigo|null, "estado": "avanzando"|"trabado"|"resuelto_por_estudiante" }`.
- **Front**: sin build, sin frameworks. KaTeX desde cdnjs, con respaldo si no carga. Funciona en celular (los estudiantes lo van a usar desde el teléfono). Diseño: el **tema Escuela Philips** del laboratorio, que está descrito en las skills del repo (`.claude/skills/`: `laboratoriobest-diseno`, `spa-recorrido-teorico-philips`, `laboratoriobest-chrome`, `tipografia-y-escala-spa`): encabezado `Escuela Philips` / título / `Matemática · 5.º año`, tipografías Hanken Grotesk + Fraunces + Fira Code, fondo papel `#FBF8F1` con grilla de cuaderno, paleta azul `#2B5A93` · ámbar `#C77A40` · verde `#45785A` · terracota `#BC5235` · violeta `#6E4EAA`, pie oficial de laboratoriobest-IA. Leer esas skills antes de escribir `web/`.
- **Acceso**: tabla `estudiantes(id EST-NN, codigo_hash)`. Códigos generados por `server/generar_codigos.py`, impresos para el docente en `datos/codigos.txt` (fuera del repo). Sin nombres, sin correos.
- **Base de datos** (SQLite, `datos/tutor.db`): `estudiantes(id, codigo_hash)`; `sesiones(id, estudiante, inicio, ultima_actividad, dispositivo)` con `dispositivo` = "celular" | "computadora" según el user-agent, sin IP ni nada más; `mensajes(id, sesion, estudiante, rol, texto, meta_json, creado)`. Una sesión se abre en el login y se considera cerrada tras 20 minutos sin mensajes; `/api/mensaje` actualiza `ultima_actividad`. Nada más se guarda: ni nombres, ni direcciones IP, ni qué hace el alumno fuera del chat.
- **Memoria acotada**: en cada llamada a la API el servidor envía el system prompt (con caché de prompt activada) y solo los **últimos 12 turnos** de la sesión, no toda la conversación. Esto mantiene el costo por turno estable en sesiones largas.
- **Límite diario**: 80 turnos por alumno por día (configurable en `server/config.py`). Al alcanzarlo, el tutor responde con un mensaje amable de "seguimos mañana" y el server no llama a la API. El contador se reinicia a las 0:00 hora de Buenos Aires.
- **Tope de gasto**: además del límite diario, el docente fija un tope mensual en la consola de la API (200 US$ para el piloto). El README lo documenta.
- **Panel docente**: ruta `/panel`, protegida con una clave de docente por variable de entorno `DOCENTE_KEY`. Muestra, por estudiante y para el curso: ingresos por semana, sesiones y minutos conectados (suma de `ultima_actividad − inicio`), turnos por sesión, dispositivo, ejercicios abordados y resueltos por el propio estudiante, proporción orientación vs. pedido de respuesta, errores frecuentes por código, escalón promedio alcanzado, ejercicios más trabados, conversaciones completas, exportación CSV de todo lo anterior. Un indicador de costo: turnos del día y del mes multiplicados por el costo medio por turno configurado en `server/config.py`.
- **Despliegue**: Dockerfile listo para Hugging Face Spaces (puerto 7860) con `ANTHROPIC_API_KEY` y `DOCENTE_KEY` como secretos. También corre local con `uvicorn server.app:app`.

## 4. Banco de plantillas (contenido verificado)

Cada plantilla es un YAML con: `id`, `tema`, `nivel` (1–5), `enunciado` (con parámetros), `rango_parametros`, `solucion_general`, `solucion_particular` (si hay condición inicial), `errores_esperados` (códigos de la sección 5), `pistas` (P1–P4). `verificar_banco.py` instancia cada plantilla en varios valores, deriva la solución, reemplaza (`simplify(lhs − rhs) == 0`), comprueba la condición inicial y, en homogéneas, el grado 0. **Nada entra al banco sin pasar la verificación.**

Temas y ecuaciones de partida (ya verificadas en el material de la unidad; usar hermanas con otros coeficientes como instancias):

| Tema | Usar | Evitar y por qué |
|---|---|---|
| Clasificación | `(y')⁴ + y'' = x` → orden 2, grado 1 | — |
| Separables | `y' = 2xy`, `y' = 3x²y`, `y' = −x/y`, `y' = x/y` | — |
| Singular | `(y')² = 4y`: general `(x + C)²`, singular `y = 0` | `y' = 2√y` (la general arrastra la restricción x ≥ −C) |
| Lineales | `y' + 2y = 6`, `y' + 3y = 12`, `y' + 4y = 8`, `y' + y = eˣ`, `y' + y/x = 3`, `y' − y/x = x` | `y' + y = x` (exige partes) |
| Homogéneas | `(2x + y)/x`, `(3x + y)/x`, `(x² + y²)/(xy)` | — |
| Física | Desintegración `N′ = −0,1N`, N(0) = 800 · Newton `T′ + kT = kT_amb`, 90 °C en 20 °C · RC descarga `R = 2000 Ω, C = 0,001 F` · RC carga `C = 0,002 F, R = 1000 Ω, E = 12 V` · RL `L = 2 H, R = 4 Ω, E = 12 V` · Caída `m = 2 kg, k = 1 kg/s, g = 10` | Dar siempre la ecuación armada: al menos un ítem por modelo da la ley con números y pide **plantear** la ecuación |

Convenciones: constante de integración **K** (C es capacidad en RC); escribir "coulomb" la primera vez; todos los modelos físicos tienen forma `y' + a·y = b`, valor final b/a, constante de tiempo 1/a. En carga RC: V(τ) = 63 % de E, media carga en RC·ln 2, no en RC.

## 5. Errores que el tutor tiene que reconocer (códigos)

| Código | Error |
|---|---|
| E01 | Leer el exponente como orden (orden vs. grado) |
| E02 | Dejar `e^{x²+C}` o escribir `e^{x²} + C`: la constante sale multiplicando, K = ±e^C |
| E03 | Reemplazar la condición inicial antes de integrar |
| E04 | Verificar una solución reemplazando un punto en vez de derivar |
| E05 | Olvidar el ½ al integrar e^{2x} (da 6 + Ke^{−2x} en vez de 3 + Ke^{−2x}) |
| E06 | Leer P sin el signo o sin dividir por el coeficiente de y′ |
| E07 | Método u·v: constante en v; entregar u en vez de u·v; integrar Q en vez de Q/v; v con el signo cambiado |
| E08 | Homogéneas: derivar `y = ux` como `y' = xu'`; al volver, no multiplicar K por x |
| E09 | Física: valor final confundido con Q; τ = 1/RC en vez de RC; en RL no dividir por L; rozamiento con signo +; k en vez de k/m |
| E10 | Pedido directo de la respuesta (no es error matemático; se registra como `tipo_pedido: respuesta`) |

## 6. Fases (cada una puede ser una sesión en la nube independiente)

**Fase 1 · Núcleo del tutor** (`tutor/`): `system_prompt.md` con las reglas de la sección 2 y el registro de errores; banco de plantillas con al menos 3 plantillas por tema (18 en total) y `verificar_banco.py` pasando; `eval/` con 8 estudiantes simulados (el que pide la respuesta de diez maneras, el que trae E02, el que trae E07, el que se traba en P3, el que resuelve bien, el que trae una ecuación que exige partes, el que escribe en lenguaje natural sin LaTeX, el que se va de tema) y un corredor que hace 10 turnos con cada uno y reporta: **cuántas veces el tutor filtró una solución completa (tiene que ser 0)**, escalón promedio, errores detectados vs. esperados.

**Fase 2 · Servidor y chat** (`server/`, `web/`): FastAPI con `/api/login`, `/api/mensaje`, `/api/historial`; SQLite; extracción y guardado del `<meta>`; front móvil con login EST-NN + código, chat con KaTeX, botón "Pista"; Dockerfile; tests de API; README con el arranque local.

**Fase 3 · Panel docente** (`panel/`, `/api/metricas`): las métricas de la sección 3, exportación CSV, vista de una conversación completa.

Fases 1 y 2 son independientes y pueden correr en paralelo (no tocan los mismos archivos). Fase 3 depende de las dos.

## 7. Cómo se verifica antes de dar por terminada una fase

- `python tutor/banco/verificar_banco.py` → 0 fallos.
- `python tutor/eval/correr.py` → informe en `tutor/eval/informe.md`; filtraciones de solución = 0.
- `pytest server/tests` en verde.
- `docker build .` y arranque local con una clave de prueba; una conversación real de 5 turnos desde el celular (o viewport 390 px en Playwright) con capturas en `NOTAS.md`.
- Revisar que ningún texto visible al estudiante contenga metalenguaje pedagógico ni la palabra "escalón".

## 8. Qué no hacer

- No guardar nombres, correos, ni ningún dato que identifique a un estudiante.
- No agregar frameworks de front, bundlers ni TypeScript.
- No subir `datos/`, `.env`, ni claves. `.gitignore` desde el primer commit.
- No cambiar las reglas de la sección 2 ni el banco de la sección 4 sin dejar nota en `NOTAS.md`.
- No mostrar al estudiante el metadato, el código de error ni el nivel de pista.
