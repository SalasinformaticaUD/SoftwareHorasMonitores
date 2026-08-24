# Informe 4 - BackCore

FECHA: 20/08/2026  
MONITOR: Juan Esteban Cañon Solorza 4:00 pm - 8:00 pm  
 
## AVANCES

* Se continuó desde los pendientes documentados en el Informe 3, sin modificar los Informes 1, 2 o 3 ni reorganizar nuevamente las carpetas de informes.
* Se configuró globalmente `ValidationPipe` con `transform`, `whitelist` y `forbidNonWhitelisted`, se verificó su uso en las suites E2E del Core y se retiraron los pipes locales duplicados.
* Se agregó un filtro global de excepciones con una respuesta uniforme que incluye código HTTP, mensaje, tipo de error, ruta y fecha del evento.
* Se completó la continuación de disponibilidad pendiente en el Informe 3:
  * `GET /disponibilidad-aulas/resumen-dia?fecha=`;
  * rango operativo inicial de `06:00` a `22:00`, configurable mediante variables de entorno;
  * ocho bloques diarios de dos horas;
  * cálculo de `siguienteActividad` desde clases, préstamos, prácticas, restricciones y tareas futuras;
  * prueba E2E que combina clase y préstamo docente y confirma la prioridad de la clase.
* Se implementó el flujo real de prácticas libres con Prisma: creación o consulta del estudiante, bloqueo por multa activa, validación de disponibilidad, creación transaccional, filtros, consulta del estudiante, finalización y cancelación.
* Se eliminó el cliente Prisma privado del módulo `software`; `SoftwareService` ahora utiliza el `PrismaService` compartido del backend.
* Se comprobó la conexión con la instancia PostgreSQL configurada. Prisma reconoce la base `Aulas`, el esquema `public` y las migraciones del proyecto.
* Se reemplazó el scaffolding de préstamos docentes por un flujo real con Prisma y los contratos de solicitud, consulta, aprobación, cancelación y finalización.
* Los préstamos validan docente existente, aula operativa, bloque de dos horas, disponibilidad y ausencia de cruces con préstamos aprobados o activos.
* Se exportó una consulta reutilizable de préstamos aprobados o activos del día para el futuro panel operativo.
* Se actualizaron únicamente las casillas efectivamente resueltas en `backend/docs/01-plan-core-operativo.md`.

## FUNCIONA

* La validación y el formato de errores se aplican globalmente al backend.
* Disponibilidad calcula consultas por bloque, resumen diario y próxima actividad sin persistir resultados.
* Prácticas libres consume el motor central de disponibilidad y protege el registro frente a multas activas.
* Los préstamos docentes se crean en estado `SOLICITADO`, pueden aprobarse, cancelarse o finalizarse según su estado y bloquean aprobaciones cruzadas.
* `GET /prestamos-docentes` permite filtrar por estado, fecha, docente y aula, con resultados ordenados para consumo operativo.
* Todos los módulos revisados utilizan el `PrismaService` compartido; ya no existe un cliente Prisma privado en `software`.
* Las 8 suites unitarias finalizan correctamente: 45 pruebas aprobadas.
* Las 7 suites E2E finalizan correctamente: 21 pruebas aprobadas.
* TypeScript, ESLint sobre los archivos modificados y `npm run build` finalizan sin errores.

## NO FUNCIONA

* La migración `20260820140000_add_fecha_asistencia_docente` está creada, pero continúa pendiente de aplicación en la instancia PostgreSQL local.
* Las pruebas del Core todavía utilizan Prisma simulado; no existe una base PostgreSQL exclusiva y aislada para pruebas automatizadas.
* La ausencia docente continúa sin liberar automáticamente el aula porque esa decisión operativa no ha sido aprobada.
* Las prácticas libres no cambian automáticamente a `VENCIDO` al superar su hora estimada.
* Préstamos docentes todavía no registra auditoría porque el módulo transversal de auditoría conserva su scaffolding.
* Auth, usuario actual y permisos siguen pendientes; por ello asistencia y operaciones auditables no obtienen todavía el usuario desde la petición.
* Observaciones operativas, tareas operativas y panel operativo conservan flujos incompletos o scaffolding.

## NO MODIFICAR

* No crear una tabla o migración para persistir disponibilidad.
* No volver a agregar operaciones de escritura al controlador de disponibilidad.
* No aceptar bloques distintos de dos horas ni bloques que comiencen en una hora impar.
* No cambiar la prioridad de disponibilidad ni liberar aulas por ausencia docente sin aprobación operativa.
* No duplicar la lógica de disponibilidad dentro de prácticas libres, préstamos docentes o panel operativo.
* No crear servicios Prisma privados por módulo; todos deben utilizar `backend/src/prisma/prisma.service.ts`.
* No aplicar migraciones ni modificar datos locales durante pruebas automatizadas sin una base exclusiva de pruebas.
* No reorganizar nuevamente `backend/Informes`; la estructura actual por frentes ya está realizada.
* No modificar los Informes 1, 2 o 3 para incorporar avances posteriores.

## SIGUIENTE PASO

* Continuar con la Semana 6 del plan: observaciones operativas que afectan disponibilidad.
* Implementar los contratos de consulta, creación, actualización y cierre lógico de observaciones.
* Diferenciar observaciones informativas de restricciones vigentes y conservar trazabilidad histórica.
* Exponer un método reutilizable para consultar restricciones vigentes sin duplicar reglas en disponibilidad.
* Agregar pruebas unitarias de vigencia y una prueba E2E de creación y consulta por aula.
* Mantener pendientes la auditoría de préstamos y el usuario autenticado hasta que los módulos transversales estén disponibles.
* Acordar con el equipo responsable la regla de ausencia docente y la política de vencimiento automático antes de cambiar esos comportamientos.
