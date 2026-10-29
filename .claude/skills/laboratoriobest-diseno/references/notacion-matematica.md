# Notación matemática — núcleo (universal)

Reglas válidas para **toda** materia del laboratorio. Lo específico de una materia (límites con tendencia, propiedades genéricas, análisis de signo, símbolos de geometría) vive en su tema.

## Fracciones — apiladas, siempre

Numerador arriba, barra, denominador abajo. **Nunca** una división en línea con `/` en contenido matemático (ni `[…]/h`, ni `u′/u`, ni `(f′g−fg′)/g²`). El componente `.fx`/`.fr` está en `assets/fraccion.css`, ya validado y sin librerías.

- El `align-items:center` del envolvente `.fx` alinea al mismo centro vertical el prefijo, el operador con su tendencia y la fracción. Sin eso, el operador queda flotando más arriba.
- Al apilar, los corchetes de agrupación del numerador **sobran**: la barra ya agrupa.
- Aplica a todo cociente, sin excepción.

## Signos y símbolos

- **Signo menos:** guion Unicode `−` (U+2212) en todo el contenido matemático. Nunca el guion ASCII `-`. Normalizar antes de entregar.
- **Diferencia de conjuntos** con `−`, no con `\`: ℝ − {a ; b}.

## Pares e intervalos

- Con **punto y coma**: `(a ; b)`, `E(−5 ; 2)`, `[2 ; +∞)`, `Γ(O ; R)`.

## Operadores

- En **redonda** dentro del contexto itálico (clase `.op`): `lim`, `sen`, `cos`, `tg`, `ln`, `log`.
