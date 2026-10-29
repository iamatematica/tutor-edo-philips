---
name: tipografia-y-escala-spa
description: "Tipografía y escala de tamaños de las SPAs de laboratoriobest-IA: qué familia va en cada rol, los pesos que se cargan, el tamaño exacto de cada elemento (títulos, cuerpo, badges, matemática), el ancho de los contenedores y qué cambia al achicar la pantalla. Usar al crear o editar cualquier SPA, widget o etiqueta de Moodle, y siempre que haya que elegir un tamaño de texto."
---

# Tipografía y escala

La escala real de las nueve SPAs de Unidad 3 y 4. No inventar tamaños: elegir de esta tabla.

Complementa `laboratoriobest-diseno` (que define la paleta, la marca y las familias) con lo
que esa skill no fija: **los tamaños**.

---

## Tres familias, tres trabajos

| Familia | Rol | Dónde |
|---|---|---|
| **Fraunces** | Títulos y marca | `h1` `h2` `h3`, nombre del laboratorio, frase del pie |
| **Outfit** | Todo el texto y la interfaz | Párrafos, opciones, botones, tablas, formularios |
| **Fira Code** | Etiquetas técnicas | Badges de sección, numeración, contadores, código |

No hay una cuarta. Un texto que no encaja en ninguno de los tres roles va en Outfit.

```html
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;1,9..144,400&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
```

```js
fontFamily: {
  display: ['"Fraunces"', 'Georgia', 'serif'],
  body:    ['"Outfit"', 'sans-serif'],
  mono:    ['"Fira Code"', 'monospace'],
}
```

**Pesos.** Fraunces solo 400 y 700 — los intermedios no se distinguen en pantalla y pesan.
Outfit en la práctica usa 400 (cuerpo), 500 (énfasis suave), 600 (botones y rótulos) y 700
(destacados). Fira Code, 400 y 500.

---

## La escala

| Rol | Tamaño | Familia | Peso | Interlineado |
|---|---|---|---|---|
| Título de portada (`h1`) | `clamp(2.6rem, 7vw, 5.6rem)` | Fraunces | 700 | `leading-none` |
| Título de pantalla (`h2`) | `text-4xl sm:text-5xl` | Fraunces | 400 | por defecto |
| Título de bloque (`h3`) | `text-xl` en tarjeta · `text-2xl` sobre navy | Fraunces | 400 | por defecto |
| **Cuerpo** | `text-sm` | Outfit | 400 | `leading-relaxed` |
| Secundario, pies, ayudas | `text-xs` | Outfit | 400 | `leading-relaxed` |
| Badge de sección | `.7rem` + `letter-spacing:.15em` + uppercase | Fira Code | 500 | — |
| Etiqueta mínima (contador, progreso) | `text-[.65rem]` + `tracking-wider` | Fira Code | 400 | — |
| Matemática KaTeX | `.katex { font-size: 1.08em }` | KaTeX | — | `.katex-display{margin:.6em 0}` |

Seis tamaños de texto y dos de título. Si hace falta un séptimo, casi siempre el problema
es de jerarquía, no de tamaño.

**El cuerpo va en `text-sm` (14 px), no en `text-base`.** Es deliberado y depende del ancho:
con los contenedores angostos de abajo, 14 px deja un renglón de 65–75 caracteres, que es la
medida cómoda de lectura. Subir a 16 px sin ensanchar el contenedor no mejora nada; ensanchar
el contenedor alarga el renglón y empeora la lectura. Los dos se mueven juntos o ninguno.

---

## Anchos

| Contenedor | Para qué |
|---|---|
| `max-w-xl` | Bajada de un título, párrafo introductorio centrado |
| `max-w-3xl` | **Columna de lectura**: teoría, ejercicios, formularios |
| `max-w-4xl` | Contenido ancho: laboratorio, tabla de errores, reporte |

El ancho lo fija el tipo de contenido, no la pantalla. Una tabla de cuatro columnas no entra
en `max-w-3xl`: va en `max-w-4xl` con su propio `overflow-x-auto`.

---

## Responsive

**Solo dos cosas cambian de tamaño al achicar la pantalla:** el `h1` de portada (por el
`clamp`) y el `h2` de pantalla (`text-4xl sm:text-5xl`). Todo lo demás es estable.

Esto es una regla, no una casualidad: multiplicar variantes por breakpoint hace que la
pantalla chica y la grande dejen de ser el mismo documento. En móvil lo que cambia es el
**layout** — las columnas se apilan, el padding se achica, las etiquetas largas se ocultan con
`hidden sm:inline` — no el tamaño del texto.

---

## Matemática

Dos regímenes. **No se mezclan en un mismo archivo.**

**Con KaTeX** (SPAs de etapas de unidad): la matemática la compone KaTeX con sus fuentes.
`.katex { font-size: 1.08em }` — el 8% de más compensa que la altura de x de KaTeX es menor
que la de Outfit; sin eso las fórmulas en línea se ven hundidas. Display math con
`margin: .6em 0 !important`.

**Matemática construida en CSS** (sin KaTeX): **STIX Two Text**, cursiva solo en las variables
— redonda en operadores, nombres de función y dígitos —, subíndices reales, y cajas de
definición en azul con filete izquierdo. El ámbar queda reservado a la voz docente. Los
radicales se dibujan en SVG estirando con el radicando: el glifo √ estirado se ve mal y el
MathML nativo no se dibuja con STIX en Chromium.

**En los dos regímenes: fracciones apiladas siempre** (`\dfrac` en KaTeX), numerador arriba y
denominador abajo. Nunca una división en línea, ni en enunciados, ni en opciones, ni en pistas,
ni en soluciones.

---

## Tracking

El espaciado de letras se usa **solo en mayúsculas y solo en Fira Code**: `.15em` en los badges
de sección, `tracking-wider` en etiquetas mínimas, `tracking-[.3em]` en el rótulo del hero.
En Outfit y en Fraunces, tracking por defecto — espaciar minúscula solo la vuelve más difícil
de leer.

---

## Verificar

1. Contar tamaños distintos de texto: si hay más de seis, sobra alguno.
2. Mirar en 400 px de ancho: nada se corta, nada desborda en horizontal.
3. Bloquear la red y recargar: con las fuentes caídas el documento tiene que seguir legible
   — de ahí que cada familia declare su respaldo (`Georgia, serif` / `sans-serif` /
   `monospace`).
4. Medir un renglón de cuerpo: entre 65 y 75 caracteres.