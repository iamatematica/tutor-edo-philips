# Notas del proyecto

Decisiones y desvíos respecto de CLAUDE.md, con fecha. Toda sesión que no pueda cumplir algo del contrato lo anota acá antes de seguir.

## 2026-10-29
- Repositorio creado con CLAUDE.md (contrato), .gitignore y estas notas. Fases 1 y 2 pueden arrancar en paralelo.
- Se agregaron a `.claude/skills/` las skills del laboratorio que las sesiones en la nube necesitan: `registro-ecuaciones-diferenciales` (contenido verificado de la unidad), `laboratoriobest-diseno`, `spa-recorrido-teorico-philips`, `laboratoriobest-chrome` y `tipografia-y-escala-spa` (tema Escuela Philips para el front). El punto "Front" de CLAUDE.md pasó a referenciar ese tema en vez de DM Sans / STIX.

## 2026-10-29 · Fase 1 (núcleo del tutor)

**Hecho**
- `tutor/system_prompt.md`: reglas de la sección 2, registro de errores E01–E10 (cada uno con una pregunta modelo), situaciones especiales (pide la respuesta, partes, lenguaje natural, fuera de tema), formato del `<meta>` y el catálogo del banco. El catálogo va entre `<!-- BANCO:INICIO -->` y `<!-- BANCO:FIN -->` y lo regenera `python tutor/banco/verificar_banco.py --actualizar-prompt`: el archivo sigue siendo la fuente única que lee el server, sin plantillas que completar.
- `tutor/metadatos.md`: esquema del `<meta>` y reglas de extracción para el server.
- `tutor/banco/`: 23 plantillas (clasificación 3, separables 4, singular 3, lineales 4, homogéneas 3, física 6), 137 instancias. `verificar_banco.py` → 0 fallos. Se probó plantando 12 errores a propósito (general con el ½ olvidado, constante sumando, singular falsa, F no homogénea, τ = 1/RC, pista que filtra la solución, `y' + y = x` en un enunciado, metalenguaje en un enunciado…): los detecta todos.
- `tutor/eval/`: 8 estudiantes simulados con guion fijo de 10 mensajes (`estudiantes.yaml`), `detector.py` (filtraciones por SymPy), `correr.py` (corredor + informe) y `turno.py` (para conducir la conversación con un tutor externo).
- Dependencias de la fase en `tutor/requirements.txt` (sympy, pyyaml, anthropic). No se tocó el `requirements.txt` de la raíz para no chocar con la fase 2, que lo crea; conviene unirlos ahí.

**Desvíos y decisiones**
- *Campos del YAML.* Además de los de la sección 4 se agregaron campos para que la verificación sea automática: `variables`, `edo` (la ecuación como F(x, y, p) = 0 con p = y′, en sintaxis SymPy), `derivados`, `condicion_inicial`, `solucion_general_implicita`, `solucion_singular`, `f_homogenea`, `control`/`controles` (valor final, τ, media carga, 63 %), `enunciado_planteo` y `parametros_simbolicos` (la k de Newton). Las soluciones van en sintaxis SymPy, no en LaTeX. `rango_parametros` acepta un dict de listas (producto cartesiano) o una lista explícita de combinaciones (LIN-01 la usa para que estén justo `y' + 2y = 6`, `y' + 3y = 12` y `y' + 4y = 8`).
- *Clasificación* no tiene solución: `solucion_general: null` y un campo `clasificacion: {orden, grado, lineal}` que el verificador recalcula.
- *Plantillas fuera de la tabla de la sección 4* (todas verificadas y con las herramientas del curso): CLA-02 `(y'')^a + b·y' = x` y CLA-03 `a·x·y''' + b·y' − y = xⁿ` (lineal); SEP-03/SEP-04 con coeficiente en `∓a·x/y`; SIN-02 (la misma `(y')² = 4a²y` con un punto: dos particulares); **SIN-03 Clairaut** `y = x·y' + a(y')²`, planteada solo como verificación (derivar y reemplazar), nivel 5; **HOM-03** `(b·x + 2y)/x`, que al separar da ∫1/(u + b) = ln|u + b|. Si el docente prefiere quedarse solo con las ecuaciones de la tabla, SIN-03 y HOM-03 se pueden sacar y siguen quedando 3 por tema salvo en singular (habría que agregar otra hermana de `(y')² = 4y`).
- *Física*: una plantilla por modelo (6). Cada una trae `enunciado` (ecuación armada) y `enunciado_planteo` (la ley con números; pide plantear). El verificador comprueba la forma y′ + a·y = b, valor final b/a, τ = 1/a y los controles de la sección 4 (media carga en RC·ln 2, V(τ) = 63 % de E).
- *El prompt no incluye las soluciones del banco*, solo enunciados, errores típicos y pistas: lo que el tutor no tiene escrito no lo puede filtrar. Para verificar un resultado del estudiante deriva y reemplaza, que es lo que pide la regla 2.
- *Filtración* (definición del corredor): una igualdad del tutor que, derivando y reemplazando con SymPy, resuelve alguna de las ecuaciones en juego (explícita o implícita, general o particular) y que el estudiante no había escrito antes; también cuenta pasar de la implícita del estudiante a la explícita, escribir el valor de K pedido, o resolver la integral por partes que trae el estudiante de partes. Es deliberadamente estricta.
- *Estudiantes con guion fijo*: los 10 mensajes no dependen de lo que conteste el tutor. Así la evaluación es reproducible y comparable entre versiones del prompt; a cambio, algunos mensajes pueden no encajar perfecto con la respuesta anterior.

**Corrida de evaluación (informe en `tutor/eval/informe.md`)**
- *Sin `ANTHROPIC_API_KEY` en la sesión.* Las 8 conversaciones no salieron de la API sino de subagentes de Claude Code (modelo Opus) que hicieron de tutor con `tutor/system_prompt.md` como única instrucción, conducidos turno a turno con `tutor/eval/turno.py` sin ver el guion. Es el mismo modelo, pero no es idéntico a producción (el subagente tiene además su propio contexto de Claude Code). **Pendiente:** con la clave, correr `python tutor/eval/correr.py` (backend `api`, modelo de `server/config.py` o `claude-opus-5-5`) y comparar.
- Resultado: **0 filtraciones** en 80 turnos; errores detectados 7/7 esperados; 80/80 metadatos válidos; 0 metalenguaje, 0 fracciones en línea, 0 herramientas fuera del curso. Escalón promedio 2,75.
- Leí las 80 respuestas a mano además del detector. No hay soluciones filtradas. Casos en el límite para que mire el docente (no son filtraciones, pero después de la cuarta pista el tutor siguió acercando):
  - EST-SIM-02, turno 6: explica $e^{3+5} = e^3 \cdot e^5$ y sugiere llamar $K$ a $e^C$; no escribe $y = Ke^{x^2}$, pero queda a un paso.
  - EST-SIM-03, turno 7: dice «integraste $Q$, pero hay que integrar $\frac{Q}{v}$»: es una corrección directa, no una pregunta (regla 3).
  - EST-SIM-04, turnos 9–10 y EST-SIM-06, turno 8: tras la cuarta pista recuerda que $\int \frac{1}{x}$ «tiene que ver con logaritmos» o que la derivada de $e^{2x}$ es $2e^{2x}$. Son fórmulas de la tabla del curso, no la solución.
  - Si se quiere más firmeza después de la cuarta pista, ajustar el párrafo «Después del cuarto escalón…» del prompt y volver a correr.
- Los "saltos de escalón" del informe (EST-SIM-02 turno 6, EST-SIM-08 turno 10) son respuestas a un avance propio del estudiante o a un pedido directo con la integral ya separada por él; no saltean pistas.
- E10 aparece también en EST-SIM-06 y EST-SIM-08 porque esos estudiantes piden una respuesta directa (la integral por partes, «pasame lo que da»): bien registrado, solo que el guion no lo listaba como esperado.
