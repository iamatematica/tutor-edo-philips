---
name: "registro-ecuaciones-diferenciales"
description: "Registro verificado para material de ecuaciones diferenciales de primer orden (secundaria técnica y primeros años): qué ecuaciones elegir, cuáles evitar, errores de criterio y modelos físicos con valores controlados."
---

# Registro · ecuaciones diferenciales de primer orden

Hechos verificados con SymPy durante la Unidad 5 de Escuela Philips (5.º año, 2026): dos SPAs de etapa (separables; lineales, homogéneas y aplicaciones), auditadas por un revisor independiente. Sirve para cualquier material nuevo de ED de primer orden: otra etapa, un TP, una actividad evaluada, el tutor de EDO.

El molde de la SPA lo da `spa-etapa-de-unidad`; el diseño, `laboratoriobest-diseno`. Acá va solo la materia.

## Antes de elegir una ecuación: qué herramientas tiene el curso

En 5.º año de Philips: derivadas, regla del producto, integrales inmediatas, ∫1/x = ln|x|, ∫e^{kx}, ∫1/(x+a) = ln|x+a| (agregarla a la tabla de fórmulas: aparece en Newton). **No** tienen integración por partes, ni el nombre "factor integrante", ni teoremas de existencia y unicidad.

Consecuencia: toda ecuación que se muestre como ejemplo, motivación o ejercicio tiene que poder resolverse con eso. Revisarlo también en las que solo se **nombran**.

## Trampas encontradas (con el arreglo)

| Trampa | Por qué es un problema | Qué usar |
|---|---|---|
| `y' + y = x` como "la ecuación que no se deja separar" | Resolverla exige ∫x·eˣ dx: partes. El alumno que la intenta se traba. | `y' + y = eˣ` (u′ = e^{2x}) o `y' + y/x = 3` (v = 1/x) |
| Solución singular con `y' = 2√y` | La general `(x + C)²` solo vale para x ≥ −C; para x < −C, y′ < 0 ≠ 2√y. Hay que arrastrar la restricción en cada frase. | `(y')² = 4y`: general `(x + C)²` sin restricción, singular `y = 0`, y de paso ejercita grado 2 |
| "Las curvas no se cruzan porque la ecuación da una sola pendiente en cada punto" | Falso como argumento: la pendiente única solo impide el cruce transversal (y = 0 toca a las parábolas de (y′)² = 4y). Además es unicidad, que no tienen. | Argumento elemental por familia: "si dos curvas y = C·eˣ pasan por el mismo punto, tienen el mismo C" |
| "El método nuevo hace falta cuando Q ≠ 0" | `y' + 2y = 6` tiene Q ≠ 0 y se separa: `y' = −2(y − 3)`. Contradicción interna. | "cuando Q depende de x" (y aun así `y' + xy = 3x` se separa: decir "en general") |
| Distractor `x = u·y` para homogéneas | Es la sustitución alternativa clásica: también funciona. Distractor válido. | `y = u + x`, `y = eᵘ` |
| Ejercicio que repite el ejemplo de la teoría | Mismo objeto y misma tarea: no mide nada (lo detecta `balance-pedagogico-spa`). | Hermano: `y' = 2xy` → `y' = 3x²y`; `(2x + y)/x` → `(3x + y)/x`; `y' + 3y = 12` → `y' + 4y = 8` |
| Aplicaciones que dan la ecuación ya armada | El programa dice "aplicaciones a la Física": lo nuevo es modelar, no resolver. Si todos los ítems traen la ecuación, el objetivo no se ejercita. | Al menos un ítem que dé la ley con números (m·v′ = m·g − k·v, L·i′ + R·i = E) y pida la ecuación |

## Errores de los alumnos que tienen que llegar a un distractor

- Orden vs. grado: leer el exponente como orden. Buen ítem: `(y')⁴ + y'' = x` → orden 2, **grado 1** (el 4 es de una derivada menor).
- Dejar `e^{x²+C}` o escribir `e^{x²} + C`: la constante sale **multiplicando**, K = ±e^C (y K = 0 recupera y = 0).
- Reemplazar la condición inicial antes de integrar.
- Verificar una solución reemplazando un punto en vez de derivar.
- Olvidar el ½ al integrar e^{2x}: da `6 + Ce^{−2x}` en vez de `3 + Ce^{−2x}` para `y' + 2y = 6`.
- Leer P sin el signo (`y' − 2xy = x` → P = −2x) o sin dividir por el coeficiente de y′ (`2y' − 4xy = 6x` → P = −2x, Q = 3x).
- Método y = u·v: ponerle constante a v; entregar u en vez de u·v; integrar Q en vez de Q/v (en `y' − y/x = x` da `x³/2 + Cx`); tomar v con el signo cambiado (en `y' + y = eˣ` da `(x + C)eˣ`).
- Homogéneas: derivar `y = ux` como `y' = xu'` (se pierde el u que después se cancela); al volver, no multiplicar la constante por x (`3x ln x + C` en vez de `3x ln x + Cx`).
- Física: valor final confundido con Q (E/R en vez de CE); constante de tiempo 1/RC en vez de RC; en RL no dividir por L (exponente −4t en vez de −2t); rozamiento con signo +; coeficiente k en vez de k/m.

## Modelos físicos verificados

Todos tienen la forma `y' + a·y = b` con a, b constantes: solución `y = b/a + K·e^{−a t}`, **valor final** b/a, **constante de tiempo** 1/a. Presentarlos juntos como "la misma forma tres veces".

| Modelo | Ecuación ordenada | Valor final | τ | Valores de control usados |
|---|---|---|---|---|
| Desintegración | N′ = −0,1·N | 0 | 10 | N(0) = 800 → N = 800e^{−0,1t} |
| Enfriamiento de Newton | T′ + kT = k·T_amb | T_amb | 1/k | 90 °C en 20 °C → T = 20 + 70e^{−kt} (K = 70, no 90) |
| Descarga RC | q′ = −q/(RC) | 0 | RC | R = 2000 Ω, C = 0,001 F → RC = 2 s; media carga en RC·ln 2 ≈ 1,39 s (no en RC, que es 37 %) |
| Carga RC | q′ + q/(RC) = E/R | CE | RC | C = 0,002 F, R = 1000 Ω, E = 12 V → 0,024 C, τ = 2 s; V(τ) = 63 % de E, V(5τ) = 99 % |
| Bobina RL | i′ + (R/L)·i = E/L | E/R | L/R | L = 2 H, R = 4 Ω, E = 12 V → i = 3(1 − e^{−2t}) |
| Caída con rozamiento | v′ + (k/m)·v = g | mg/k | m/k | m = 2 kg, k = 1 kg/s, g = 10 → v = 20(1 − e^{−0,5t}) |

Cuidado con la letra C: en RC es la capacidad. Llamar K a la constante de integración y avisarlo en el enunciado. Escribir "coulomb" la primera vez que aparece la unidad C.

## Laboratorios que funcionaron

- **Campo de direcciones con clic = condición inicial.** RK4 con h = 0,01 en los dos sentidos, corte si |pendiente| > 60 o sale del recuadro. Para `−x/y` y `x/y`, rechazar clics con |y| < 0,15 (divide por cero) y avisarlo. Controles: la curva de `y' = y` por (0 ; 1) coincide con eˣ a 1e−6; la de `−x/y` por (0 ; 2) queda sobre x² + y² = 4 a 1e−4.
- **Carga del capacitor con deslizadores R, C, E.** Eje t fijo de 0 a 20 s (si se reajusta, dos curvas distintas se ven iguales: ver `graficos-canvas-educativos`), línea punteada en E, marca de τ al 63 %. La pregunta de predicción "si duplicás R" y la conclusión "el voltaje final depende solo de E" funcionan bien juntas.
- **Campo de una homogénea** `(x² + y²)/(xy)` con rectas punteadas por el origen: sobre y = 2x todas las flechas tienen pendiente F(2) = 2,5. Necesita una pregunta; sin tarea el panel no se mira.

## Cómo se verifica

En SymPy, para cada ítem: derivar la solución y reemplazar (`simplify(lhs − rhs) == 0`), comprobar la condición inicial, y **comprobar que cada distractor no es solución**. En homogéneas, comprobar grado 0: `simplify(F(λx, λy) − F(x, y)) == 0`. Las cuentas físicas (RC, CE, L/R, mg/k) van también al autotest `?test` de la SPA.