# Marca — núcleo laboratoriobest-IA

La marca es lo único de identidad **común a todas las materias**. La paleta, las tipografías de texto y el chrome completo dependen del **tema** de cada materia (ver `tema-analisis.md`, `tema-geometria.md`). La marca en HTML listo para pegar está en `assets/marca.html`.

## La marca (obligatoria, dos variantes según el fondo)

El nombre va **todo junto, sin espacios**: `laboratoriobest-IA`, en **Fraunces bold**, precedido por un **bullet circular terracota**. Si el contenedor es flex, **sin `gap`**: el gap separaría los fragmentos del nombre. El margen (7px; 5px en chico) va **solo en el bullet**.

**Variante A — sobre pastilla crema** (`#faf8f1`, la más usada en header y footer):
- `laboratorio` → `#20201c` · `best` → `#b57d4c` · `-IA` (guion incluido) → `#415a8e` · bullet `#b57d4c`.
- Bajada: "Prof. Ariel L. Cardozo Delgado" en `#6579a1`, chica, alineada con el inicio del texto (`padding-left:15px`).

**Variante B — directa sobre fondo oscuro** (sin pastilla):
- `laboratorio` → `#f5efe3` (crema claro) · `best` → `#c98b52` · `-IA` → `#8ba7dd` · bullet `#b57d4c`.

Regla de oro: pastilla-crema **o** fondo-oscuro-directo según el fondo. Nunca `laboratorio` oscuro (#20201c) sobre oscuro: no se lee.

**Ubicaciones típicas:** header (derecha) · footer · marca de agua gigante en banners de tema (`rgba(255,255,255,.04)`) · versión chica en la esquina de cada tarjeta de ejercicio.

## Footer — invariante

Cualquiera sea el tema, el footer lleva **siempre**:
1. La frase, en Fraunces itálica: **"La matemática no exige genios, exige constancia."**
2. Los profesores **de esa materia** (los define el tema: Análisis → Cardozo · Mosquera; Geometría II → Cardozo · Chaparro).
3. La marca.

## Tipografía de la marca

- **Fraunces** (con eje óptico `opsz`) para la marca y los títulos — común a todos los temas.
- La tipografía de **texto/interfaz** la fija cada tema (Análisis: Outfit; Geometría II: Hanken Grotesk).
- **Matemática inline:** `'Cambria Math','Times New Roman',serif` en **itálica**, en todos los temas. Nunca sans para las fórmulas.
