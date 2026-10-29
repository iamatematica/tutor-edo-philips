---
name: "laboratoriobest-diseno"
description: "Sistema de diseño único de laboratoriobest-IA (Prof. Ariel Cardozo, INSPT-UTN), organizado en un NÚCLEO neutro (marca, fracción apilada, notación universal, técnica del sandbox, validación) más un TEMA por materia (Análisis Matemático I; Geometría II; Escuela Philips). Consultá esta skill SIEMPRE que construyas o edites cualquier SPA, recurso HTML educativo, etiqueta de Moodle o material del laboratorio, aplicando el núcleo y encima el tema de la materia correspondiente."
---

# Sistema de diseño laboratoriobest-IA

Fuente única de verdad del diseño, la notación, la pedagogía y la técnica del laboratorio del Prof. Ariel Cardozo (INSPT-UTN). Está en **dos capas**: un **núcleo neutro**, común a toda materia, y un **tema** por materia que apoya encima. No es una skill que se invoca sola para producir un entregable: es la que las skills de género referencian, y la que Claude consulta antes de tocar cualquier recurso del laboratorio.

## Cómo se usa

1. **Aplicar el núcleo** siempre (marca, fracción apilada, notación universal, desarrollo sin saltos, técnica, validación).
2. **Aplicar el tema** de la materia encima (paleta, tipografía de texto, chrome, notación y pedagogía propias).
3. Desde otra skill: esa skill aporta su estructura propia (pestañas por tema, figuras, etc.) y delega en el núcleo + el tema con una línea del tipo "aplicar `laboratoriobest-diseno` (núcleo + tema-…)".

## Núcleo (común a toda materia)

- **Marca `laboratoriobest-IA`** toda junta, sin espacios, bullet terracota adelante, sin `gap` (margen solo en el bullet). Dos variantes de color según el fondo. → `references/marca-y-paleta.md`, `assets/marca.html`.
- **Footer** con la frase *"La matemática no exige genios, exige constancia."*, los profesores de la materia y la marca.
- **Fracción apilada, siempre** (numerador arriba, barra, denominador abajo). Nunca división en línea. → `assets/fraccion.css`, `references/notacion-matematica.md`.
- **Notación universal:** menos Unicode `−`, diferencia de conjuntos con `−`, pares e intervalos con punto y coma, operadores en redonda; sumatorias con límites explícitos (`\sum_{n=0}^{\infty}`, no `\sum_{n \ge 0}`). → `references/notacion-matematica.md`.
- **Desarrollo sin saltos, nunca.** Ver la sección de abajo: es regla permanente de Ari para todo material.
- **Técnica del sandbox:** cero handlers inline (event delegation), `scrollIntoView` en vez de `scrollTo`, sin `localStorage` en el preview, archivo autónomo; más el fix del scroll vertical espurio y la macro de KaTeX. → `references/tecnica.md`.
- **Validar antes de entregar:** normalizar guiones → `node --check` → funcional (Playwright/jsdom) → verificación matemática → control de pasos (abajo) → `present_files` con tabla de respuestas. → `references/tecnica.md`.

## Desarrollo sin saltos (regla permanente)

Ari lo pidió como regla para siempre: **no se saltea ningún paso, aunque sea trivial.** Vale para todo lo que muestre una cuenta resuelta: ejemplos, resoluciones de ejercicios, feedback que traiga números, recuadros de error (mal / bien), paneles de los exploradores, guías docentes y claves de corrección.

Cada cálculo se escribe en cuatro tiempos, en la misma cadena de igualdades:

1. **La fórmula general** (la derivada o la expresión, antes de evaluar).
2. **La misma fórmula con los valores sustituidos**, tal cual, sin operar.
3. **Cada operación intermedia**: lo de adentro del paréntesis, cada producto, cada suma.
4. **El resultado.**

Así:

- Bien: R_T = −0,04 (T − 60) = −0,04 (50 − 60) = −0,04 · (−10) = 0,4.
- Mal: R_T = −0,04 (T − 60) = 0,4.

Lo que más se saltea, y no se saltea más:

- **Evaluar una función o una trayectoria:** T(5) = 40 + 2 · 5 = 40 + 10 = 50, no T(5) = 50.
- **Derivar antes de evaluar:** escribir la derivada como expresión (f_x = 2x + 3y) y recién después reemplazar.
- **Los productos y las sumas finales:** 11 · 2 + 3 · 2 = 22 + 6 = 28, no 11 · 2 + 3 · 2 = 28.
- **Comprobar que el punto pertenece** a la curva o superficie antes de usarlo: 1 · 2 + 2² − 6 = 2 + 4 − 6 = 0.
- **Despejes:** 1,84 − 0,1792 t = 0 ⇒ 0,1792 t = 1,84 ⇒ t = 1,84 sobre 0,1792 (apilada) ≈ 10,27.
- **Simplificar una fracción:** decir por cuánto se simplifica.
- **Verificaciones por otro camino:** también completas (la expansión, la derivada, el valor).

Dónde va el desarrollo completo:

- **Toda pregunta con cuentas lleva resolución paso a paso**, también las de opción múltiple.
- **El feedback breve no reemplaza la resolución.** Si el feedback da números, van completos; si no, da el resultado, una línea de interpretación y remite a "Ver resolución paso a paso".
- **Paneles dinámicos de los exploradores:** cada modelo trae la expresión con los valores sustituidos (funciones del tipo `fxL(a, b, x, y)` que devuelven "−0,04 (T − 60) = −0,04 (50 − 60) = −0,04 · (−10)"), y cada trayectoria trae su posición y velocidad sustituidas. Si la velocidad es constante, no se repite el mismo número dos veces ("T′ = 2", no "T′ = 2 = 2").

**Control antes de entregar:** recorrer cada "=" de cada desarrollo y preguntarse si un alumno pasa de la izquierda a la derecha sin hacer ninguna cuenta mentalmente. Si tiene que hacer una, falta un paso. Este control se hace leyendo el texto renderizado (`innerText` con acordeones, resoluciones y paneles abiertos), no el fuente.

## Temas (uno por materia)

- **Análisis Matemático I** → `references/tema-analisis.md` + `assets/chrome-analisis.html`. Paleta navy/blue, Outfit, equipo Cardozo · Mosquera, notación de AMI (límites con tendencia, variable `a`, paréntesis abiertos) y pedagogía (`references/pedagogia.md`).
- **Geometría II** → `references/tema-geometria.md`. Papel cálido + grilla, Hanken Grotesk, equipo Cardozo · Chaparro; el detalle fino vive en la skill `spa-resoluciones-geo2`.
- **Escuela Philips (Matemática · 5.º año)** → el detalle vive en la skill `spa-recorrido-teorico-philips`. Encabezado `Escuela Philips` / título / `Matemática · 5.º año` (sin sigla ni puntos medios), Fraunces + Hanken Grotesk + Fira Code, papel `#FBF8F1` con grilla de cuaderno, paleta azul `#2B5A93` · ámbar `#C77A40` · verde `#45785A` · terracota `#BC5235` · violeta `#6E4EAA`, KaTeX con `\lim` → "lím" y respaldo sin conexión, voseo, actividades intercaladas y práctica de 12 ejercicios en tres niveles de 4 con la misma consigna.

## Recursos

- `references/marca-y-paleta.md` — núcleo: la marca (dos variantes) y el footer invariante.
- `references/notacion-matematica.md` — núcleo: notación universal (con la fracción apilada).
- `references/tecnica.md` — núcleo: sandbox, layout, KaTeX y el checklist de validación.
- `references/tema-analisis.md` — tema AMI: paleta, tipografía, chrome, notación y pedagogía de Análisis.
- `references/pedagogia.md` — pedagogía de AMI (asíntotas, racionales, monotonía, andamiaje).
- `references/tema-geometria.md` — tema Geometría II (registro; el detalle está en `spa-resoluciones-geo2`).
- `assets/marca.html` — marca neutra + footer, para pegar (núcleo).
- `assets/chrome-analisis.html` — head + header + footer completos del tema AMI.
- `assets/fraccion.css` — componente de fracción apilada validado (núcleo).