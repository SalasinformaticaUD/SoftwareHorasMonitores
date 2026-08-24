# Contrato de disponibilidad de aulas

Fecha de publicacion: 21/08/2026

La disponibilidad se calcula bajo demanda en bloques exactos de dos horas. Ninguno de
estos endpoints crea o modifica una tabla de disponibilidad.

## Endpoints

- `GET /disponibilidad-aulas?fecha=YYYY-MM-DD&horaInicio=HH:00&horaFin=HH:00`
- `GET /disponibilidad-aulas/:aulaId?fecha=YYYY-MM-DD&horaInicio=HH:00&horaFin=HH:00`
- `GET /disponibilidad-aulas/resumen-dia?fecha=YYYY-MM-DD`

`horaInicio` debe ser una hora par y `horaFin` debe corresponder exactamente a dos
horas despues.

## Respuesta por aula

| Campo                | Tipo               | Descripcion                                                            |
| -------------------- | ------------------ | ---------------------------------------------------------------------- |
| `aula`               | objeto             | Identidad, ubicacion, capacidad y estado fisico del aula.              |
| `bloque`             | objeto             | Fecha, inicio, fin y duracion del bloque consultado.                   |
| `estadoCalculado`    | enum               | `disponible`, `ocupada`, `reservada`, `mantenimiento` o `bloqueada`.   |
| `motivo`             | string             | Explicacion legible de la decision de mayor prioridad.                 |
| `bloqueActual`       | fuente o `null`    | Primera fuente que explica el estado actual.                           |
| `siguienteActividad` | actividad o `null` | Actividad posterior mas cercana durante el mismo dia.                  |
| `fuentes`            | lista              | Fuentes encontradas para el bloque, ordenadas por prioridad.           |
| `calculadoEn`        | fecha ISO          | Momento en que se realizo el calculo.                                  |
| `persistido`         | `false`            | Confirma que el resultado fue calculado y no almacenado.               |

`aula` contiene `id`, `codigo`, `ubicacion`, `capacidad` y `estado`. `bloque`
contiene `fecha`, `horaInicio`, `horaFin` y `duracionHoras`.

Cada fuente contiene `tipo`, `id`, `descripcion` y opcionalmente `estado`. Los tipos
permitidos son `estado-aula`, `restriccion`, `clase-programada`,
`prestamo-docente`, `practica-libre` y `tarea-operativa`. Una
`siguienteActividad` agrega `horaInicio` y `horaFin`.

## Resumen diario

El resumen devuelve `fecha`, `rangoOperativo`, `bloques`, `calculadoEn` y
`persistido: false`. Cada elemento de `bloques` contiene `horaInicio`, `horaFin` y la
lista de respuestas de disponibilidad para todas las aulas.

La definicion TypeScript se encuentra en
`src/disponibilidad-aulas/entities/disponibilidad-aula.entity.ts`.
