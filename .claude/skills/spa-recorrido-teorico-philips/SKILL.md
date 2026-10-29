---
name: "spa-recorrido-teorico-philips"
description: "Construir una SPA de recorrido teórico interactivo a partir de un apunte PDF para Escuela Philips (5.º año): teoría en el orden del apunte con actividades intercaladas, ejemplos en pasos, laboratorio con lectura del gráfico y práctica de 12 ejercicios en tres niveles."
---

# SPA de recorrido teórico · Escuela Philips

Género: el docente pasa un **apunte de teoría en PDF** (definiciones, cajas de concepto clave, ejemplos resueltos, ejercicios con solución, "Repaso: somos capaces") y pide "armá una SPA basándote en este documento". El resultado es un solo archivo HTML que **sigue el orden del apunte** y lo convierte en un recorrido con actividades cortas, ejemplos en pasos desplegables, un laboratorio y una práctica graduada. Referencias construidas: `series-de-potencias.html` y `serie-fourier-rampa-geogebra.html` (Colegio Philips 2026).

Antes de escribir código: leer el PDF completo, ofrecer con una pregunta corta el formato (recorrido teórico / etapa de unidad / solo resoluciones) y si se agregan ejercicios extra, y **verificar toda la matemática con SymPy** primero. Aplicar `laboratoriobest-chrome` (con la variante Philips de abajo) y el núcleo de `laboratoriobest-diseno`; los gráficos del laboratorio siguen `graficos-canvas-educativos`; si el apunte trae una construcción en GeoGebra, esa sección sigue `geogebra-embebido-spa`; auditar con `auditoria-spa-educativa` antes de entregar.

## Tema Escuela Philips (difiere del tema AMI)

- **Encabezado**: primera línea `Escuela Philips` (sin sigla ni puntos medios), segunda el título del recurso en Fraunces, tercera `Matemática · 5.º año`. Pastilla crema de la marca con la bajada `Prof. Ariel L. Cardozo Delgado`. Pie: frase + pastilla, nada más. El nombre del profesor aparece exactamente 2 veces.
- **Tipografía**: Fraunces (títulos, marca), **Hanken Grotesk** (cuerpo, no Outfit), Fira Code (badges, contadores). Cuerpo 15 px.
- **Fondo**: papel `#FBF8F1` con grilla de cuaderno (`linear-gradient` 28 px, azul al 7 %).
- **Paleta**: azul `#2B5A93`, ámbar `#C77A40`, verde `#45785A`, terracota `#BC5235`, violeta `#6E4EAA`; navy del chrome `#0f2244`.
- **Roles de color**: cajas de definición/teorema en azul con filete izquierdo; cajas "Ejemplo" con cabecera ámbar (como las del apunte); notas de voz docente en ámbar claro; avisos ("no podemos afirmar nada") en terracota; actividades con filete superior verde; laboratorio con filete violeta.
- **Lengua**: voseo rioplatense ("Calculá", "Probalo"), aunque el apunte use "Calculad". Sin metalenguaje pedagógico visible. **Registro neutro, sin jerga que envejece**: nada de "de un tiro", "al toque", "manso"; preferir "en un solo paso", "tranquilo". Las metáforas que nombran el fenómeno sí se quedan ("el gráfico engaña", "el \(2^n\) no alcanza para frenar al factorial").

## Lo que el alumno ya tiene: el límite duro del material

**Antes de elegir el camino de cada resolución, listar qué herramientas tiene el curso y no usar ninguna otra.** En 5.º año de Philips, para series: \(\sqrt[n]{n} \to 1\), límites de cocientes de polinomios por grado y coeficiente principal, series conocidas (armónica, armónica alternada, series \(p\), geométrica), condición necesaria y Leibniz; para Fourier, además, integración por partes, paridad y \(\cos(n\pi) = (-1)^n\). **No** tienen el teorema del encaje, resultados del tipo "la raíz \(n\)-ésima de cualquier polinomio tiende a 1", ni el valor \(\ln 2\) de la armónica alternada.

Consecuencia práctica: cuando un ejercicio exigiría un resultado que no tienen, **cambiar de criterio en vez de enunciar el resultado sin probarlo**. Ejemplo real: para \(a_n = \dfrac{n^2+3}{n\,4^n}\), la raíz pide \(\sqrt[n]{n^2+3} \to 1\) (que solo se justifica encajando entre \(\left(\sqrt[n]{n}\right)^2\) y \(\left(\sqrt[n]{n}\right)^3\)); el cociente, en cambio, deja \(\dfrac{1}{4}\cdot\lim \dfrac{n^3+2n^2+4n}{n^3+n^2+3n+3} = \dfrac{1}{4}\), que es exactamente lo que saben hacer. Se elige el cociente y la raíz no aparece.

Una frase del tipo "se puede probar que…", o un valor que "se sabe" (como \(2\ln 2\)), dentro de una solución o un feedback es una señal de alarma: o se justifica con lo que tienen, o se acota con lo que tienen ("queda entre 1 y 2"), o se cambia el camino, o se saca.

## Estructura (una sección por bloque del apunte)

Navegación sticky con pestañas numeradas; secciones alternadas con `.sec-visible` / `.sec-hidden` (`position:absolute; left:-99999px; visibility:hidden`, nunca `display:none`, para que KaTeX mida bien). Al cambiar de sección, `section.scrollIntoView({block:'start'})` con `scroll-margin-top` igual a la altura de la barra, y **desplazar la barra de pestañas para que la activa quede visible** (`navInner.scrollLeft = boton.offsetLeft - navInner.clientWidth/2 + boton.offsetWidth/2`): en móvil, si no, la pestaña activa queda fuera de pantalla.

0. **Inicio**: idea central en una frase, caja "Punto de partida", tarjetas de ruta a cada sección, nota "Cómo usar este recorrido".
1..n. **Secciones teóricas** en el orden del apunte. Cada una: badge "Sección k", `h2`, bajada, cajas de definición, ejemplos, **una o dos actividades "Probalo"**, botón "Seguir · k+1 · …" al pie.
- **Laboratorio**: exploración visual del objeto central (ver abajo).
- **Ejercicios**: 12 en tres niveles (ver abajo).
- **Repaso**: checklist "Somos capaces" tomada del apunte + cuestionario final de 6 preguntas con explicación por opción y puntaje; al menos una pregunta de interpretación con contexto real.

## Figuras: lo que el texto nombra, el dibujo lo marca

Si un ejemplo dice "fijate en el gráfico: en \(x = 4\) la rampa ya volvió a empezar", el punto \(x = 4\) tiene que estar **marcado en la figura** (punto, guía punteada al eje, rótulo con el valor), en un color distinto del de la función (ámbar). Una figura que solo muestra el objeto general obliga al alumno a ubicar a ojo un punto que el texto da por visto: el docente lo detecta enseguida ("no veo x = 4"). Mismo criterio para las escalas: si el texto pregunta por \(x = \pi\), el eje va graduado en múltiplos de \(\pi\), en el SVG, en el canvas y en GeoGebra.

## Actividades intercaladas (tarea distinta de la teoría, nunca recalcular lo ya calculado)

- **Opción múltiple** con feedback específico por opción (`.opt[data-ans]`, `data-ok="1"` en la correcta, `.fb[data-fb=k]`): identificar objetos (centro y coeficiente), reconocer qué es y qué no es, elegir el método más cómodo.
- **Verdadero/falso** (`.juicio[data-vf][data-ok="V|F"]`): afirmaciones sobre un caso con datos. Si una afirmación es *indecidible* con los datos, no marcarla "falsa": reformularla como "Se puede asegurar que…".
- **Auditá el razonamiento**: tres soluciones de estudiantes con los errores frecuentes (una correcta); el alumno juzga "bien / mal". Todo error que el material declare frecuente tiene que llegar a una tarea de juzgar.
- **Mini-comprobación numérica**: dos o tres campos con Comprobar, para reemplazar en una fórmula recién obtenida (p. ej. \(b_1, b_2, b_5\)).
- Pasos de los ejemplos en desplegables `.paso` numerados; la consigna invita a anticipar el paso antes de abrirlo.

### En las opciones va la decisión; el desarrollo va en el feedback

Regla dura para toda opción múltiple, y sobre todo para las de "¿qué método conviene?":

- **Opciones simétricas**: todas de largo y forma parecidos, cada una nombra la decisión y da **una razón de una línea**, sin cálculos ni límites resueltos. Una opción que muestra el desarrollo se delata sola por la forma (es la más larga y la más "trabajada") y además anula la pregunta: el alumno tenía que anticipar qué va a pasar con cada método, no leerlo ya hecho. Si dos opciones traen un valor numérico y dos no, también se delatan: o todas o ninguna.
- **Nada de distractores de relleno** del tipo "ninguno de los dos sirve", "da igual", "no se puede saber sin graficar", "es un error de redondeo del programa" o "no está definida": son falsos de un modo que nadie elige y dejan la pregunta en dos o tres opciones. Cada distractor tiene que ser un **error real** que un alumno comete (p. ej. "la raíz, desarrollando antes \((n+1)!\) como producto", "el cociente, porque las potencias se cancelan" cuando las bases son distintas, olvidar el coeficiente, restar dos períodos en vez de uno, tomar el valor de un lado del salto, creer que el pico baja con más términos).
- El cálculo completo va en el **feedback de cada opción**, y el feedback del distractor explica por qué ese camino no cierra, no solo que está mal.

### El desarrollo sigue el camino del lápiz

El alumno escribe **una sola fracción grande** y simplifica adentro; no separa el cociente en un producto de dos cocientes ya resueltos. Descomponer de entrada ("la parte del factorial da \(n+2\) y la de la potencia da \(\dfrac{1}{4}\)") es una reescritura que hace quien ya sabe el resultado, y al que recién aprende le aparecen dos fracciones de la nada. Por eso, en actividades, pistas y soluciones el criterio del cociente se muestra así:

1. el cociente entero, apilado: \(\alpha = \lim \dfrac{\;\dfrac{a_{n+1}\text{ completo}}{\;}\;}{\dfrac{a_n\text{ completo}}{\;}}\);
2. pasado a una sola fracción (multiplicando por el recíproco), todavía sin simplificar;
3. una línea de texto que dice **qué se cancela y por qué** (\((n+2)! = (n+2)(n+1)!\), \(4^{n+1} = 4\cdot 4^n\));
4. el límite ya simplificado y el radio.

Mismo criterio para la raíz: primero \(\sqrt[n]{|a_n|}\) con el coeficiente completo adentro, después la simplificación. Y para integración por partes: elegir \(u\) y \(dv\) con la razón ("se simplifica al derivar" / "se sabe integrar"), aplicar la fórmula, resolver la integral que queda, controlar derivando, evaluar, y recién ahí simplificar.

## Laboratorio

Selector de casos o deslizador (`<option>` sin fórmulas ni barras: "xⁿ sobre n·3ⁿ (centro 0, R = 3)"), la fórmula en KaTeX debajo, chips "ir a …" (deshabilitados cuando no aplican), una recta o figura SVG con el estado, un canvas con los datos (sumas parciales, etc.) y un panel de estado. El dibujo sigue `graficos-canvas-educativos`: escala vertical con marcas redondas (o en múltiplos de \(\pi\) si el tema lo pide), rótulos medidos que nunca se cortan, notación compacta para valores grandes y ejes que dicen qué representan (`N · términos sumados`, `Sɴ · suma parcial`). En rótulos de canvas, subíndices con dígitos Unicode (`S₁₀`, no `S10`, que se lee como número) y sin fracciones en línea (`altura de cada barra: |bₙ|`, no `2/n`).

El panel lleva **dos capas**: qué dice la teoría para ese valor (adentro / afuera / en el borde / caso trivial) y una **"Lectura del gráfico"** calculada con los propios datos: línea plana, se aplana en un nivel, alterna acercándose, crece cada vez más despacio sin aplanarse ("el gráfico no decide"), paso parejo o ida y vuelta sin achicarse (el término no tiende a cero), se dispara. En los bordes el texto dice "todo indica que…" y remite a la teoría; nunca decide por el dibujo. Acompañar con una tarjeta **"Cómo leer el gráfico"** (tabla: lo que ves · qué está pasando · qué concluís) y la regla "60 (o 200) términos no demuestran nada sobre una suma infinita". Probar las lecturas en una tabla de casos (centro, adentro, cada borde, afuera, casos degenerados) antes de entregar.

### Las lecturas tienen que coincidir con el número que se muestra al lado

El texto de cada rama se escribe para un rango de valores, y el panel muestra el número real a centímetros. Si la rama "N ≤ 10" dice "el máximo todavía no llega a \(\pi\)" y el panel muestra 3,166, el material se contradice solo. Antes de entregar:

- tabular el dato clave (máximo, error, sobrepaso) para **cada frontera de rama** y un valor interior (N = 1, 2, 3, 4, 5, 10, 30, 60, 100, 200);
- partir la rama donde el fenómeno cambia (en la rampa de Fourier: N ≤ 4 "no llega a π" / N ≤ 10 "ya pasa");
- revisar la **dirección** de cada verbo: el pico de Gibbs **sube** hacia su límite, no "baja" ni "no baja de"; un sobrepaso negativo no se muestra como porcentaje sino como "todavía no llega".

Mismo control para la tabla "Cómo leer" y para los feedbacks de las actividades del laboratorio.

## Práctica: 12 ejercicios, 4 por nivel, misma consigna

- **Niveles 1, 2 y 3, cuatro ejercicios cada uno, numerados 1–12.** Los rótulos son solo "Nivel 1/2/3": nada de "procedimiento completo" ni etiquetas que sugieran tareas distintas, porque la consigna es la misma en todos. No hay grupo "Del apunte": los del apunte que entren se reparten por nivel.
- Nivel 1 fija los casos arquetípicos; nivel 2 agrega variantes (centro desplazado, valores fraccionarios, señal escalada o corrida, objetos que hay que reescribir); nivel 3 son ejercicios de formato de examen o con contexto real, idealmente los que aporta el docente.
- **Mezcla de resultados variada dentro de cada nivel** para que no se adivine por patrón.
- Cada ejercicio: enunciado en display, campos de respuesta (número/fracción/"inf"/expresión con "pi" + selects de casos; el placeholder puede mostrar "1/7" o "pi/2" como instrucción de tipeo), botón Comprobar (también Enter), **3 pistas graduadas** a demanda, "Ver solución" completa con pasos, estado y contador de resueltos. Feedback distinto para el error típico (p. ej. "escribiste β en vez de 1/β", "falta el factor 2 de la paridad").
- Datos en un array `EJ`. Para series de potencias: `id, nivel, rot, tex, c, R, Rtex, izqTex/derTex (cuando el valor simplificado sea más claro), ext, pistas[3], sol, lnA` (ln|aₙ| para el autotest numérico). Para temas con varios valores por ejercicio (Fourier): `id, nivel, tit, enun, campos[{k, tex, resp, tol?, sel?, errs[[valor, mensaje]]}], pistas[3], sol`. Al filtrar o reducir, regenerar la numeración.
- Índices: si el término no está definido en n = 0 (división por cero), la serie empieza en n = 1 aunque el apunte diga n = 0; anotarlo en la auditoría.

### Cada enunciado se sostiene solo

El alumno llega a un ejercicio desde el filtro de nivel, o salteando, o días después: **no puede depender de la teoría ni de otro ejercicio**. Cada enunciado trae todo lo que se usa en su desarrollo:

- la función **con su intervalo y su período** ("Sea \(f(x) = x\) en \((-\pi\,;\,\pi)\), extendida con período \(2\pi\)"), aunque sea la misma de toda la SPA;
- la **definición de todo símbolo** que aparece en los campos (\(S_N(x) = 2\sum_{n=1}^{N}\ldots\), y si ayuda, el primer caso: \(S_1(x) = 2\,\sen x\));
- la **fórmula o el resultado previo** que el ejercicio aplica, como "Dato:" explícito (los \(b_n\) de la función base cuando se pide escalarla o correrla; la serie que se va a evaluar; la regla del promedio en un salto);
- **nunca** "del ejercicio 6", "compará con el ejercicio 5", "la rampa corrida de antes", "con la fórmula de la sección 3". Si dos ejercicios usan la misma función, se repite.

Control antes de entregar: leer cada enunciado aislado y preguntar "¿de dónde saca el alumno cada número que aparece en la solución?"; buscar `ejercicio \d+` y `anterior` dentro del bloque `EJ` (tiene que dar vacío).

### Ningún campo se responde copiando el enunciado

Si el enunciado escribe "\(\pi = 4(1 - \tfrac13 + \ldots)\)" y un campo pide "el límite exacto", ese campo es gratis. Reemplazarlo por algo que exija trabajo con esos datos (el error de la aproximación, cuántos términos, una cota).

## Notación

- Sumatorias con **límites explícitos** `\sum_{n=0}^{\infty}`; si el apunte usa `\sum_{n \ge 0}`, agregar una nota ámbar "Otra forma de escribirlo" que la presente como equivalente.
- Unificar `a_n`, `c` en todo el recorrido aunque el apunte mezcle `C_n`, `x_0`. Si el apunte escribe `sin` (como GeoGebra) y la clase usa `sen`, escribir \(\sen\) (macro `\sen` → `\operatorname{sen}`) y aclararlo una vez en una nota.
- Fracciones siempre `\dfrac` (también en bases, en etiquetas de campos y en feedback; nunca `\frac`, `\tfrac` ni `f(\pi/2)` en una etiqueta); intervalos con punto y coma `(-3\,;\,3)`; menos Unicode en el texto. En un `<option>` no se puede apilar: elegir opciones sin fracción (`3x` en vez de `x/2`).
- No reutilizar un nombre con dos significados en la misma SPA (si \(g\) es el recorte en GeoGebra, la rampa corrida de un ejercicio se redefine en su propio enunciado).

## Técnica

- KaTeX 0.16.9 por CDN (`\[ \]`, `\( \)`), macros `\neq`/`\ne` → `\mathrel{\text{\char"2260}}`, `\lim` → `\mathop{\text{lím}}\limits`, `\sen` → `\operatorname{sen}`. `ignoredTags` incluye `code`. `.katex{font-size:1.08em}`, `.katex-display{overflow-x:auto;overflow-y:hidden!important}`.
- **Respaldo sin KaTeX**: si `renderMathInElement` no existe al arrancar, `window.__katexFailed = true` y un conversor mínimo TeX→HTML (`.mfall`: `\dfrac` → `.frac` apilada, `\sum`/`\lim` con límites, `\sqrt[n]`, símbolos, variables en cursiva). Cero LaTeX crudo visible sin conexión.
- Etiquetas en mayúsculas (`text-transform:uppercase`) que contienen matemática: `label .katex, label .mfall{text-transform:none}`.
- Event delegation, sin handlers inline; `scrollIntoView`; `localStorage` con clave versionada envuelto en try/catch, restaurando sección, actividades, ejercicios (valores, estado, pistas), cuestionario y checklist.
- Mensaje de "falta elegir" en un select: renderizar el TeX de la etiqueta (`Falta elegir una opción en \(${tex}\)`), no limpiarlo con regex (sale "pi,;,pi").
- Panel `?test` que llena `window.__TESTS__`: radio numérico de cada serie desde `lnA` (cociente en N = 5000) o coeficientes por integración numérica según el tema, valores de control del laboratorio (ln 3, 2, e − 1, −ln 2, máximos de sumas parciales…), analizador de respuestas, cada ejercicio acepta su respuesta oficial y rechaza una incorrecta con un mensaje por campo, estructura (12 ids únicos, 4 por nivel, 3 pistas, `ext` coherente con R cuando aplica, una sola opción correcta y un feedback por opción en cada actividad), cero `.katex-error`, nombre del profesor 2 veces.
- Canvas: ver `graficos-canvas-educativos`.

## Validación (en este orden)

1. SymPy: radio por cociente y por raíz y `Sum.is_convergent` en los extremos de **todas** las series (ejercicios, ejemplos, laboratorio), o coeficientes, sumas parciales y máximos según el tema; respuestas de los 12 ejercicios y del cuestionario. Si SymPy se cuelga en una, verificarla a mano y con mpmath o el límite del término.
2. `node --check` del JS extraído.
3. Playwright con el CDN interceptado y servido desde `node_modules/katex` (`page.route` + `fulfill`), y otra corrida con todo bloqueado para el respaldo. Resolver los 12 ejercicios programáticamente, recargar y comprobar la persistencia. El panel `?test` tapa botones: hacer los clics con `evaluate(... .click())`.
4. Agente revisor especialista sobre el código fuente (matemática, opciones, coherencia, fracciones con barra, metalenguaje, lengua) y aplicar todo. Pasarle la tabla de valores verificados y pedirle expresamente que revise **la simetría de las opciones** (ninguna se delata por su forma), que ningún distractor sea de relleno, que los desarrollos sigan el camino del lápiz, que **ningún paso use una herramienta que el curso no tiene**, que **cada lectura del laboratorio coincida con el número mostrado en todo el rango de su rama** y que **cada enunciado se sostenga solo**.
5. Pasadas de `auditoria-spa-educativa` (texto visible, desborde a 1280/1024/820/390, estrés, 2×, persistencia, sin conexión) + tabla de lecturas del laboratorio + verificación por píxeles de los rótulos del canvas + mirar cada figura buscando los puntos que el texto nombra.
6. Chrome: nombre del profesor 2 veces, `brand-inspt` y `brand-sub` una vez, marca junta (0 px).
7. Entregar el archivo, guardar `claude/<tema>.html` y `claude/auditoria-<tema>.md` en el proyecto con la tabla de respuestas; en la respuesta, una línea de resultado y solo las decisiones que le tocan al docente.