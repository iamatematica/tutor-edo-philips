# Pedagogía — principios del laboratorio

Cómo se enseña, no solo cómo se ve. Estas decisiones se repiten en las SPA de Análisis Matemático I.

## Asíntotas: el límite es el método, no un accesorio

- **AV:** los **dos límites laterales** explícitos, con la lectura del tipo `c²/0⁺ = +∞`.
- **AH:** descarte con el **límite en el infinito** desarrollado (dividiendo por la mayor potencia). Presentar los casos por comparación de grados como tabla.
- **AO:** con las definiciones `m = lim(x→∞) f(x)/x` y `b = lim(x→∞) [f(x) − m·x]`, cada límite resuelto. La **división de polinomios queda solo como verificación breve al final**, nunca como método principal.
- La fórmula de la homográfica (`AH = a/c`, `AV = −d/c`) se presenta como el método general aplicado a ese caso, **no** como fórmula mágica.

## Funciones racionales: hueco vs. asíntota vertical

Es el corazón del tema. Ante un factor común en numerador y denominador: explicitar el dominio, advertir que la raíz común **no** es cero de la función, e identificar la **discontinuidad evitable ("hueco")** frente a la AV genuina. El "mito de la asíntota intocable" (que la curva nunca puede cruzar una AH) se desarma explícitamente.

## Monotonía y signo, tramo por tramo

- Análisis de signo/monotonía **tramo por tramo** en lista, con paréntesis abiertos en los puntos críticos (ver notación). El punto crítico se excluye porque ahí la función no crece ni decrece.
- Nada de etiquetas `f>0 / f<0` encima de los gráficos: el análisis de signo va en el texto. No marcar máximos/mínimos locales sobre el gráfico.
- Si hay raíz doble, explicar **por qué** el punto se excluye.

## Factorización de cuadráticas

Por suma y producto de raíces (`r₁+r₂` = opuesto del coeficiente lineal, `r₁·r₂` = término independiente), no solo con la resolvente.

## Estructura y andamiaje

- **Máximo detalle:** cada paso enuncia **qué se hace y por qué** (la propiedad o definición que lo habilita), con el desarrollo línea por línea.
- **Dos actos** cuando aplica (visto en la Unidad 3 — derivadas): primero *aprender la técnica* (definición → reglas → cadena), después *usar la derivada* (tangente, física, sucesivas). El concepto geométrico (derivada = pendiente de la tangente) nace en la etapa de definición, así que la técnica puede reordenarse sin perderlo.
- **No regalar resultados** que el alumno ya puede calcular: si en su punto del recorrido ya tiene las reglas, el ejercicio no debe decir "sabiendo que f′(x)=…". El prerrequisito de cada etapa debe coincidir con lo realmente aprendido antes.
- **Respuesta final desplegable** (caja verde, cerrada por defecto): el alumno intenta antes de mirar.
- **Retroalimentación** por nivel (inicial/intermedio/avanzado) en los cierres integradores.
