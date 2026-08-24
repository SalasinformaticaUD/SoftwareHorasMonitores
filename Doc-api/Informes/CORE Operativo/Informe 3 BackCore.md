# Informe 2 - BackCore

FECHA: 20/08/2026  
MONITOR: Pablo Garzon Gomez

## AVANCES

* Se continuó el flujo establecido por el Informe 1 con el tercer paso del plan del Core: asistencia docente asociada a clases programadas.
* Se reemplazó el CRUD genérico de asistencia por los contratos específicos:
  * `GET /asistencia-docente?fecha=&aulaId=&estado=`;
  * `POST /asistencia-docente`;
  * `PATCH /asistencia-docente/:id`;
  * `GET /asistencia-docente/clase/:claseId`.
* Se agregó `fecha` al modelo `AsistenciaDocente` para identificar la ocurrencia diaria de una clase semanal.
* Se creó la migración `20260820140000_add_fecha_asistencia_docente` con una restricción única para `(claseId, fecha)` y un índice para consultas por fecha y estado.
* Los DTOs validan clase, fecha en formato `YYYY-MM-DD`, estado, usuario registrador opcional y observación de hasta 500 caracteres.
* Se verifica que la clase programada exista antes de registrar o consultar asistencias.
* Durante el MVP, si se recibe manualmente `registradoPorId`, se verifica que el usuario exista.
* Se evita más de un registro para la misma clase y fecha tanto desde el servicio como mediante la restricción única de PostgreSQL.
* Los estados permitidos son `PENDIENTE`, `ASISTIO` y `AUSENTE`.
* Los registros pendientes mantienen `registradaEn` en `null`; al confirmar asistencia o ausencia se guarda automáticamente el momento del registro.
* La consulta general permite filtrar por fecha, aula y estado, preparando la consulta de pendientes del día para el panel operativo.
* La consulta por clase devuelve el historial ordenado desde la fecha más reciente.
* El endpoint de actualización no permite cambiar la clase ni la fecha, protegiendo la identidad del bloque operativo.
* Se agregaron pruebas unitarias y E2E para creación, estados, referencias inexistentes, duplicados, filtros, historial, actualización y validación de entrada.

## FUNCIONA

* La asistencia docente usa persistencia Prisma y ya no devuelve textos de scaffolding.
* Solo se puede registrar asistencia sobre una clase programada existente.
* Una clase admite un único registro por fecha y puede conservar historial en fechas diferentes.
* Las asistencias pueden consultarse por fecha, aula, estado y clase programada.
* Los cambios a `ASISTIO` o `AUSENTE` registran automáticamente el momento de confirmación.
* Los errores de duplicado y referencias inexistentes se convierten en respuestas HTTP claras.
* El esquema Prisma actualizado es válido y el cliente fue regenerado.
* Las 5 suites unitarias finalizan correctamente: 27 pruebas aprobadas.
* Las 4 suites E2E finalizan correctamente: 10 pruebas aprobadas.
* Prettier, TypeScript, ESLint y `npm run build` finalizan sin errores.

## NO FUNCIONA

* No se ejecutaron pruebas manuales contra la instancia PostgreSQL configurada; las pruebas automatizadas usan Prisma simulado para no modificar datos locales.
* La migración de asistencia está creada, pero todavía no se aplicó sobre la instancia PostgreSQL local.
* `registradoPorId` todavía no se obtiene automáticamente del usuario autenticado porque la infraestructura de autenticación no está integrada con este flujo.
* El cálculo dinámico de disponibilidad sigue pendiente.
* Las prácticas libres, préstamos docentes, observaciones restrictivas y panel operativo siguen pendientes.
* El `ValidationPipe` todavía no está configurado globalmente para todo el backend; está aplicado directamente en los controladores implementados.

## NO MODIFICAR

* No retirar la fecha operativa ni la restricción única `(claseId, fecha)` de asistencia docente.
* No permitir que `PATCH /asistencia-docente/:id` cambie la clase o la fecha del registro.
* No aceptar estados diferentes a `PENDIENTE`, `ASISTIO` y `AUSENTE`.
* No crear una tabla permanente para disponibilidad; debe calcularse desde las fuentes operativas.
* No conectar directamente con la base de Gestión de Monitores.
* No reemplazar `PrismaService` con servicios Prisma privados en los siguientes módulos del Core.
* No modificar las relaciones o enums del Core sin revisar las migraciones y el impacto sobre los demás frentes.
* No construir el panel operativo duplicando reglas de asistencia o disponibilidad.

## SIGUIENTE PASO

* Continuar con el cuarto paso del plan: implementar el motor calculado de disponibilidad de aulas.
* Crear y validar los contratos:
  * `GET /disponibilidad-aulas?fecha=&horaInicio=&horaFin=`;
  * `GET /disponibilidad-aulas/:aulaId?fecha=&horaInicio=&horaFin=`;
  * `GET /disponibilidad-aulas/resumen-dia?fecha=`.
* Definir una respuesta estable con aula, estado calculado, motivo, bloque actual, siguiente actividad y fuentes que explican el resultado.
* Mantener disponibilidad como un cálculo de solo lectura, sin persistir una tabla de disponibilidad.
* Aplicar la prioridad definida en el plan: estado del aula, restricción vigente, clase programada, préstamo docente, práctica libre, tarea que afecta disponibilidad y disponible.
* Definir explícitamente cómo una asistencia `AUSENTE` modifica o explica la ocupación producida por una clase programada.
* Agregar pruebas unitarias para prioridades y pruebas E2E con aula disponible, aula ocupada y aula en mantenimiento.
* No implementar todavía los CRUD reales de prácticas libres, préstamos docentes, observaciones o panel operativo.
