# Metadato estructurado por turno

Cada respuesta del tutor termina con un bloque `<meta>…</meta>` que contiene **un objeto JSON en una sola línea**. El servidor lo extrae, lo guarda junto al mensaje y lo **borra** del texto antes de mostrárselo al estudiante. El panel docente calcula sus métricas a partir de estos campos.

```
<meta>{"ejercicio": "LIN-01", "tipo_pedido": "orientacion", "escalon": 3, "error_detectado": null, "estado": "avanzando"}</meta>
```

## Campos

| Campo | Tipo | Valores | Significado |
|---|---|---|---|
| `ejercicio` | string \| null | id de plantilla del banco (`"SEP-01"`, `"FIS-04"`, …) o `null` | Ejercicio en el que se está trabajando. `null` si es una ecuación propia del estudiante, una pregunta de teoría o no hay ejercicio. |
| `tipo_pedido` | string | `"orientacion"`, `"respuesta"`, `"verificacion"`, `"conversacion"` | Qué pidió el estudiante en el mensaje al que se responde. `"respuesta"` = pidió la solución (corresponde al código E10 del registro de errores). |
| `escalon` | entero | `0` a `4` | Pista dada **en este turno**: 1 pregunta de orientación, 2 idea clave, 3 primer paso hecho, 4 integral o ecuación auxiliar planteada. `0` si no hubo pista (verificación, conversación). Nunca pasa de 4. |
| `error_detectado` | string \| null | `"E01"` … `"E09"` o `null` | Error del registro que el tutor nombró (con una pregunta) en este turno. E10 no va acá: se registra como `tipo_pedido: "respuesta"`. |
| `estado` | string | `"avanzando"`, `"trabado"`, `"resuelto_por_estudiante"` | `trabado`: pidió dos o más pistas seguidas sin mostrar avance o dijo que no sabe seguir. `resuelto_por_estudiante`: el tutor verificó (derivando y reemplazando) que el resultado del estudiante es correcto. |

## Reglas de extracción (servidor)

- Se toma el **último** bloque `<meta>…</meta>` del mensaje; se eliminan todos los bloques del texto visible.
- Si falta o el JSON es inválido, se guarda el mensaje igual con `meta = null` y se registra el problema; nunca se le muestra el bloque al estudiante.
- Valores fuera del esquema se guardan tal cual en una columna cruda y se normalizan a `null` en las columnas tipadas.

## Validación

`tutor/eval/correr.py` valida el esquema en cada turno y reporta el porcentaje de metadatos válidos. La función de referencia es `validar_meta()` en `tutor/eval/correr.py`.
