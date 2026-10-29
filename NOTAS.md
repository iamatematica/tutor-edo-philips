# Notas del proyecto

Decisiones y desvíos respecto de CLAUDE.md, con fecha. Toda sesión que no pueda cumplir algo del contrato lo anota acá antes de seguir.

## 2026-10-29
- Repositorio creado con CLAUDE.md (contrato), .gitignore y estas notas. Fases 1 y 2 pueden arrancar en paralelo.
- Se agregaron a `.claude/skills/` las skills del laboratorio que las sesiones en la nube necesitan: `registro-ecuaciones-diferenciales` (contenido verificado de la unidad), `laboratoriobest-diseno`, `spa-recorrido-teorico-philips`, `laboratoriobest-chrome` y `tipografia-y-escala-spa` (tema Escuela Philips para el front). El punto "Front" de CLAUDE.md pasó a referenciar ese tema en vez de DM Sans / STIX.
- Decisiones de datos y costo (acordadas con el docente): tabla `sesiones` explícita (inicio, última actividad, dispositivo), memoria acotada a los últimos 12 turnos, límite de 80 turnos por alumno por día, tope mensual de 200 US$ en la consola de la API; el panel suma ingresos por semana, minutos conectados y un indicador de costo. Estimación de referencia: 35 alumnos, 3 sesiones/semana de hasta 80 turnos, 4 semanas → ≈ 200 US$ con Sonnet 5.5 como techo.
