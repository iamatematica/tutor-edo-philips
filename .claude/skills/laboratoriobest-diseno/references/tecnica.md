# Técnica — sandbox, componentes y validación

Guardarraíles que hacen que las SPA funcionen tanto en el iframe de Claude.ai como publicadas en GitHub Pages e incrustadas en Moodle.

## Sandbox y compatibilidad Moodle

- **Cero handlers inline** (`onclick=…`): fallan en el iframe sandboxeado. Toda interactividad por **event delegation**: `document.addEventListener('click', e => { const t = e.target.closest('[data-…]'); … })`. Funciones expuestas en `window.` si hace falta.
- **`scrollIntoView({block:'start', behavior:'instant'|'smooth'})`** en vez de `window.scrollTo` (poco fiable en iframes sandboxeados).
- **Sin `localStorage`/`sessionStorage` en el preview de Claude.ai** (lanza excepción en el sandbox). Si una SPA de etapas persiste progreso con un `STORE_KEY` en producción (GitHub Pages/Moodle), envolver todo acceso en `try/catch` y degradar sin romper.
- Autónoma: un solo archivo, CSS y JS embebidos, sin más dependencia externa que Google Fonts (y KaTeX si es SPA de laboratorio).
- Bloques "Etiqueta" de Moodle: CSS 100% inline (los `<style>` se filtran).

## Detalles de layout aprendidos

- **Sin deslizadores verticales espurios.** `overflow-x:auto` hace que el navegador calcule `overflow-y` como `auto` y aparece una barra vertical sobre fórmulas y tablas. Fijar `overflow-y:hidden !important` en los contenedores con scroll horizontal (`.katex-display`, steppers, tabs) y `resize:none` en los textarea. Un `autoGrow()` hace crecer los textarea con el contenido (re-ejecutar al cambiar de etapa).
- Flexbox `gap` en el contenedor de la marca separa los fragmentos del nombre: el margen va **solo** en el bullet.
- Acordeones/pasos: `scroll-margin-top:70px`, y al abrir, si la cabecera quedó tapada por la barra sticky (`rect.top < 70`), `scrollIntoView({block:'start'})`.

## KaTeX (solo SPA de laboratorio interactivo)

Las resoluciones de examen usan CSS serif y **no** cargan KaTeX. Si la SPA es de laboratorio interactivo con KaTeX 0.16.9, el `≠` compuesto (`\neq`) usa un carácter del área privada de las fuentes KaTeX y se ve como caja rota cuando esas fuentes no cargan (Moodle, visor, PDF). Arreglo obligatorio — reemplazarlo por un glifo único:

```js
macros: {
  '\\neq': '\\mathrel{\\text{\\char"2260}}',
  '\\ne':  '\\mathrel{\\text{\\char"2260}}',
}
```

Usar `\char"2260`, no el carácter `≠` literal (KaTeX lo remapea a `\ne` y entra en bucle). Verificar con fuentes cargadas y bloqueadas (`page.route('**/*.woff2', abort)`): en ambos casos el `≠` debe verse limpio y el DOM no debe contener `.katex .vbox`.

## Checklist de validación (antes de entregar)

En este orden:

1. **Normalizar guiones:** todo menos matemático a `−` (U+2212).
2. **`node --check`** sobre el JS extraído (sintaxis).
3. **Funcional:** Playwright headless si está disponible (pestañas cambian, acordeones abren/cierran, colores computados = hex de la especificación, marca "laboratoriobest-IA" toda junta con 0 px entre fragmentos). Si Playwright no está, jsdom con canvas stubbeado como mínimo.
4. **Matemática:** verificar **toda** respuesta final con cálculo independiente (SymPy: `diff()`, `simplify(resultado − esperado) == 0`) contra una tabla de respuestas esperadas. Idealmente generar el contenido programáticamente desde esas mismas fórmulas. Reportar N/N correctas al docente.
5. **Entregar** con `present_files` y un resumen con la tabla de respuestas para que el profesor verifique.
