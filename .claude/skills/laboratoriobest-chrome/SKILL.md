---
name: laboratoriobest-chrome
description: "Encabezado y pie oficiales de las SPAs de laboratoriobest-IA (Prof. Ariel L. Cardozo Delgado): dónde va la institución, la materia y el título; qué lleva y qué no lleva el pie; y cuántas veces puede aparecer el nombre del profesor. Usar SIEMPRE que se cree o se edite cualquier recurso HTML del laboratorio — SPA de resoluciones de examen, laboratorio interactivo, widget suelto o etiqueta de Moodle —, aunque el pedido no mencione el encabezado ni el pie, y aunque otra skill (spa-resoluciones-examen, spa-laboratorio-matematico, spa-laboratorio-canvas, spa-resoluciones-geo2, laboratoriobest-diseno) describa un chrome distinto. En caso de contradicción sobre header o footer, manda esta skill."
---

# Encabezado y pie de las SPAs de laboratoriobest-IA

**El contexto académico va una sola vez, en el encabezado. El pie cierra con la frase y la marca.**

Esta skill define solamente el chrome. Todo lo demás del sistema de diseño —paleta,
tipografías, fracciones apiladas, notación— lo definen las skills de género y
`laboratoriobest-diseno`.

En `assets/chrome.html` está el HTML y el CSS ya validados: **copiarlos tal cual** y
cambiar solo los tres textos señalados. No reescribir el chrome desde cero.

---

## Encabezado

Fondo degradado navy (`#0f2244 → #1a3a6e`). A la izquierda, tres líneas de arriba
hacia abajo:

1. **Institución**, en celeste, con puntos medios entre las letras de la sigla:
   `U·N·S·A·M · EEyN`, `I·N·S·P·T · UTN`.
2. **Título del recurso**, en Fraunces blanco: "Resoluciones · TP Límite y Continuidad".
3. **Materia**, en azul claro y tamaño chico: "Análisis Matemático I".

A la derecha, la pastilla crema (`#faf8f1`) con la marca y su bajada.

La tercera línea lleva **solo la materia**. No se acredita ahí al profesor titular ni a
la cátedra de origen: el recurso es del laboratorio, y atribuirlo a una cátedra que no lo
produjo confunde sobre quién lo hizo. Si hace falta nombrar la cátedra o el apunte de
origen, va en el enunciado del ejercicio o en una nota al pie del contenido, nunca en el
chrome.

## Pie

Fondo navy, centrado, **dos elementos y nada más**:

1. La frase, en Fraunces itálica: *"La matemática no exige genios, exige constancia."*
2. La pastilla crema con la marca y su bajada.

**No lleva línea de profesores.** Esa línea existía cuando el recurso tenía dos autores y
la pastilla acreditaba a uno solo; con un único autor repite palabra por palabra la bajada
del logo, a pocos centímetros de distancia. Tampoco repite la institución ni la materia,
que ya están en el encabezado.

**Única excepción:** si el recurso tiene más de un autor, entra una línea entre la frase y
la pastilla con los coautores separados por punto medio ("Prof. Ariel Cardozo · Prof.
Pablo Mosquera"). La bajada de la pastilla sigue siendo la del logo y no cambia.

## Dónde aparece el nombre, y cuántas veces

"Prof. Ariel L. Cardozo Delgado" aparece **exactamente dos veces** en el archivo, y siempre
como bajada del logo (`.lab-sub`): una en la pastilla del encabezado y otra en la del pie.
Nunca suelto, fuera de la marca.

En las tarjetas de ejercicio va la marca en **versión chica, sin bajada y sin pastilla**,
con los colores originales sobre blanco.

## La marca, recordatorio

Va toda junta, sin espacios: "laboratorio" en `#20201c`, "**best**" en terracota `#b57d4c`,
"**-IA**" en azul `#415a8e`, precedida por un puntito circular terracota. Si el contenedor
usa flexbox, **sin `gap`**: el margen va solo en el puntito, porque el `gap` separa los
tres fragmentos del nombre.

---

## Verificación antes de entregar

Correr sobre el HTML final. Las cuatro tienen que dar bien:

```python
import re, io
s = io.open(ARCHIVO, encoding="utf-8").read()

# 1. el nombre aparece 2 veces, las dos dentro de un .lab-sub
assert s.count("Ariel L. Cardozo Delgado") == 2

# 2. el pie no tiene línea de profesores (salvo coautoría)
pie = re.search(r"<footer.*?</footer>", s, re.S).group(0)
assert "footer-profs" not in pie

# 3. institución y materia, una sola vez cada una, en el encabezado
assert len(re.findall(r'class="brand-inspt"', s)) == 1
assert len(re.findall(r'class="brand-sub"', s)) == 1

# 4. la marca se lee junta: en Playwright, separación 0 px
#    entre .lab, .best y .ia dentro de .lab-name
```

Si alguna falla, corregir antes de entregar: no es una observación a criterio del docente.
