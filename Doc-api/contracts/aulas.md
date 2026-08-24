# Contrato de aulas para frontend

Fecha de confirmacion: 21/08/2026

Este contrato se contrasto con `Frontend/src/features/aulas/types.ts` y
`Frontend/src/features/aulas/components/RoomsView.tsx`, y quedo publicado para el
frontend en `Frontend/src/features/aulas/api-types.ts`. Los campos minimos para el
listado y detalle de aulas se obtienen mediante `GET /aulas` y `GET /aulas/:id`.

## Respuesta publica

| Campo API            | Uso en frontend                       | Regla                                                                          |
| -------------------- | ------------------------------------- | ------------------------------------------------------------------------------ |
| `id`                 | `Room.id`                             | UUID estable del aula.                                                         |
| `codigo`             | `Room.code`                           | Identificacion visible del aula.                                               |
| `ubicacion`          | `Room.location`                       | Ubicacion completa.                                                            |
| `piso`               | `Room.floor`                          | Se deriva de `ubicacion`; puede ser `null` si no contiene el texto `Piso N`.   |
| `capacidad`          | `Room.capacity`                       | Cantidad total de puestos.                                                     |
| `estado`             | Estado fisico                         | `OPERATIVA`, `MANTENIMIENTO` o `FUERA_DE_SERVICIO`.                            |
| `caracteristicas`    | Hardware, puestos y datos adicionales | JSON controlado por el modulo de aulas.                                        |
| `proyectoCurricular` | `Room.curriculumProject`              | Proyecto asociado, cuando exista.                                              |
| `software`           | `Room.software`                       | Lista normalizada con id, nombre, version, descripcion y fecha de instalacion. |
| `historial`          | `Room.history`                        | Ultimos diez eventos operativos, ordenados del mas reciente al mas antiguo.    |

El historial basico consolida instalaciones de software, observaciones, tareas,
limpiezas, practicas libres y prestamos docentes. Cada entrada contiene `id`, `fecha`,
`tipo`, `descripcion` y `responsable`; este ultimo puede ser `null` cuando el modelo de
origen aun no registra usuario responsable.

## Estado fisico y disponibilidad

`Aula.estado` no representa ocupacion en tiempo real. Los estados visuales
`disponible`, `en-clase` y `reservada` deben obtenerse desde
`GET /disponibilidad-aulas`. El frontend puede combinar ambos contratos usando el UUID
del aula, sin inferir disponibilidad a partir del estado fisico.

Los campos de demostracion `licenses` y `status` de cada software no forman parte del
modelo persistente actual. Deben tratarse como opcionales en el adaptador del frontend
hasta que exista una regla de negocio y persistencia aprobadas para licenciamiento.
