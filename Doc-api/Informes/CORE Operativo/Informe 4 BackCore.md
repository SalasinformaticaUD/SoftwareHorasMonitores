# Informe 3 - BackCore

FECHA: 20/08/2026  
MONITOR: Ivan Felipe Prado Blanco 8:00am - 10:00am // 2:00pm - 4:00pm

## AVANCES

* Se continuó el recorrido progresivo de `backend/docs/01-plan-core-operativo.md` desde las reglas generales del frente.
* Se resolvió la regla: "La disponibilidad se calcula, no se guarda como tabla permanente".
* La regla quedó actualizada con `[X]` en el plan del Core y se documentó que el cálculo se realiza en bloques de dos horas.
* Se reemplazó el scaffolding CRUD de `disponibilidad-aulas` por un módulo de consulta de solo lectura.
* Se eliminaron los DTOs vacíos `CreateDisponibilidadAulaDto` y `UpdateDisponibilidadAulaDto`.
* Se creó `ConsultarDisponibilidadDto` para validar fecha, hora de inicio y hora de finalización.
* Los bloques deben durar exactamente dos horas, comenzar en una hora par y usar horas completas con formato `HH:00`.
* Las fechas y horas operativas se interpretan para la zona horaria `America/Bogota`.
* Se implementaron los contratos:
  * `GET /disponibilidad-aulas?fecha=&horaInicio=&horaFin=`;
  * `GET /disponibilidad-aulas/:aulaId?fecha=&horaInicio=&horaFin=`.
* Se retiraron las rutas `POST`, `PATCH` y `DELETE` de disponibilidad.
* `DisponibilidadAulasService` utiliza el `PrismaService` compartido y calcula el estado al momento de cada consulta.
* El cálculo revisa las siguientes fuentes:
  * estado operativo del aula;
  * restricciones vigentes;
  * clases programadas;
  * asistencia docente de la fecha;
  * préstamos docentes aprobados o activos;
  * prácticas libres activas;
  * tareas operativas que afectan disponibilidad.
* Se implementó la prioridad: estado físico del aula, restricción, clase, préstamo docente, práctica libre, tarea operativa y disponible.
* Una asistencia docente en estado `AUSENTE` se incluye como señal explicativa, pero no libera automáticamente el aula.
* La respuesta incluye aula, bloque evaluado, estado calculado, motivo, fuente prioritaria, fuentes encontradas, fecha del cálculo y el indicador `persistido: false`.
* Se confirmó que no existe modelo, tabla ni migración de disponibilidad en Prisma.
* Se agregaron pruebas unitarias para disponibilidad sin actividades, prioridad de mantenimiento, ausencia docente, consulta de todas las aulas y validación de bloques.
* Se agregaron pruebas E2E para consultas generales e individuales, validación de entrada y ausencia de endpoints de escritura.
* Se ajustó la importación de Jest en una prueba previa de asistencia docente para conservar compatibilidad con TypeScript durante la verificación general.

## FUNCIONA

* La disponibilidad se calcula dinámicamente y no se persiste.
* Se puede consultar la disponibilidad de todas las salas para un bloque de dos horas.
* Se puede consultar una sala específica mediante UUID.
* Los bloques con duración diferente de dos horas son rechazados.
* Los bloques que comienzan en horas impares son rechazados.
* Un aula sin actividades ni restricciones retorna `disponible`.
* Un aula en mantenimiento retorna `mantenimiento` aunque tenga una clase programada.
* Una clase programada retorna el aula como `ocupada` y expone la señal de asistencia correspondiente.
* Las restricciones y tareas pueden bloquear el aula.
* Los préstamos docentes y prácticas libres pueden reservar el aula.
* El controlador de disponibilidad solo expone operaciones `GET`.
* Las 6 suites unitarias finalizan correctamente: 33 pruebas aprobadas.
* Las 5 suites E2E finalizan correctamente: 13 pruebas aprobadas.
* Prettier, TypeScript, ESLint y `npm run build` finalizan sin errores.

## NO FUNCIONA

* `GET /disponibilidad-aulas/resumen-dia?fecha=` todavía no está implementado.
* No está definido el rango operativo diario que se dividirá en bloques de dos horas para construir el resumen del día.
* `siguienteActividad` permanece en `null`; todavía no se busca la próxima actividad posterior al bloque consultado.
* Falta una prueba E2E que combine aula, clase y préstamo docente dentro del mismo escenario de prioridad.
* Las pruebas nuevas utilizan Prisma simulado y no validan el cálculo contra una base PostgreSQL exclusiva para pruebas.
* La ausencia docente no libera el aula porque esa decisión operativa todavía no ha sido aprobada.
* Los módulos reales de prácticas libres, préstamos docentes, observaciones y tareas todavía deben completar sus propios flujos; disponibilidad ya puede leer sus registros cuando existan.
* El `ValidationPipe` todavía no está configurado globalmente para todo el backend.

## NO MODIFICAR

* No crear una tabla, modelo o migración para guardar resultados de disponibilidad.
* No volver a agregar endpoints `POST`, `PATCH` o `DELETE` al módulo de disponibilidad.
* No aceptar bloques con duración diferente de dos horas.
* No aceptar bloques que comiencen en una hora impar.
* No cambiar la prioridad de las fuentes sin acordar primero la regla operativa.
* No liberar automáticamente un aula por ausencia docente sin aprobación del equipo responsable.
* No duplicar estas reglas dentro de prácticas libres, préstamos docentes o panel operativo; esos módulos deben consumir el servicio del Core.
* No reemplazar el `PrismaService` compartido con un servicio Prisma privado para disponibilidad.
* No modificar el Informe 1 BackCore; los avances posteriores deben continuar en los informes siguientes.

## SIGUIENTE PASO

* Continuar desde el inicio del plan con el siguiente punto pendiente: configurar un `ValidationPipe` global.
* Registrar en `main.ts` las opciones `transform`, `whitelist` y `forbidNonWhitelisted`.
* Verificar mediante pruebas E2E que la validación global conserve el comportamiento de aulas, horario, asistencia y disponibilidad.
* Retirar configuraciones locales duplicadas únicamente después de verificar la configuración global.
* No avanzar al filtro global de excepciones hasta cerrar la validación global.
* Como continuación posterior de disponibilidad, acordar el rango operativo diario antes de implementar `resumen-dia` y calcular `siguienteActividad`.
* Nota para el próximo monitor: revisar que `backend/Informes` esté organizado en las tres carpetas correspondientes a Core operativo, Plataforma e integración y Módulos paralelos solamente si esa reorganización todavía no se ha completado. No mover nuevamente los informes si la estructura ya está correcta.
