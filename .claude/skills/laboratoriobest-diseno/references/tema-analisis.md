# Tema Análisis Matemático I

Capa visual y de notación propia de AMI, encima del núcleo. Equipo: **Prof. Ariel Cardozo · Prof. Pablo Mosquera**. Chrome listo en `assets/chrome-analisis.html`.

## Paleta y tipografía

```
--navy:#0f2244   --blue:#1d6fcc   --blue2:#2d82e6   --teal:#0ea5e9   --sky:#38bdf8
--bg:#eef6ff     --bg2:#f8fbff    --white:#fff
--g50…--g800     (slate: #f8fafc → #1e293b)
--ok:#059669     --ok-bg:#d1fae5  --warn:#d97706
--r:12px  --rl:16px  --rxl:24px   --sh:0 4px 6px -1px rgba(0,0,0,.08),0 2px 4px -1px rgba(0,0,0,.05)
```

- Texto/interfaz en **Outfit** (300–800). Títulos y marca en Fraunces (núcleo).
- Tarjetas blancas, `border-radius:16px`, sombra `--sh`, borde `--g200`. Fondo general `--bg`; canvas sobre `--bg2` o `#f7faff`.
- Hero/banner navy: `linear-gradient(135deg,#0f2244,#1a3a6e)`. Variante ancha: `linear-gradient(120deg,#0d2559,#16428f 48%,#1f57b4)`.
- Contraste: texto sobre navy pasa WCAG AA (≥ 4.5:1).

## Header y footer (AMI)

- **Header** (`.topbar`): navy degradado. Izquierda: `I·N·S·P·T · UTN` en celeste, título en Fraunces blanco, "Análisis Matemático I · Prof. Ariel Cardozo · Prof. Pablo Mosquera". Derecha: marca variante A.
- **Footer**: navy, frase + los dos profesores + marca (núcleo).
- **Variante B de marca** (crema sobre navy, sin pastilla): en las SPA de etapas de la Unidad 3, pie `#131f3d`.

## Notación propia de AMI

- **Límites:** tendencia explícita en subíndice (`x→∞`, `x→a⁺`, `h→0` en `<sub>`).
- **Paréntesis abiertos** en ceros, puntos críticos y asíntotas de los conjuntos de signo/monotonía (en un punto crítico la función no crece ni decrece → se excluye).
- **Variable `a`** (no `u`) en las propiedades genéricas de módulo, raíz y logaritmo. Excepción: en la regla de la cadena se admite `u = g(x)` si el docente lo aprueba; ante la duda, preguntar.
- "coeficiente principal" (no "coeficiente líder").
- Inline math destacado sobre fondo azulado tenue (clase `.math`).

## Pedagogía

La pedagogía de AMI (asíntotas por límites, hueco vs. AV, monotonía tramo por tramo, factorización, estructura en dos actos) está en `pedagogia.md`.
