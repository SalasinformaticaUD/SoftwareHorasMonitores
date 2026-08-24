# Informe 1 - BackCore

FECHA: 20/08/2026  
TURNO: 10:00 a. m. - 14:00 p. m.  
MONITOR: Pablo Garzon Gomez

## AVANCES

* El módulo `aulas` permite crear, listar, consultar, actualizar y eliminar aulas mediante las rutas REST definidas en el plan.
* Se implementaron validaciones de código, ubicación, capacidad, características, estado y proyecto curricular.
* El listado de aulas permite filtrar por estado, ubicación y proyecto curricular, e incluye el proyecto y el software instalado.
* Se controla el código duplicado, la inexistencia de aulas o proyectos y la eliminación de aulas con historial operativo.
* Cuando un aula tiene clases, prácticas, préstamos, observaciones o tareas asociadas, no se elimina físicamente y debe cambiarse a `FUERA_DE_SERVICIO`.
* Se creó un `PrismaModule` global y un `PrismaService` compartido para los módulos del Core.
* Se completó el segundo paso del plan: base real de períodos académicos y clases programadas dentro de `horario`.
* Se reemplazó el CRUD genérico de horario por los contratos específicos:
  * `GET /horario/periodos`;
  * `POST /horario/periodos`;
  * `PATCH /horario/periodos/:id/activar`;
  * `GET /horario/clases?aulaId=&periodoId=&diaSemana=`;
  * `POST /horario/clases`;
  * `PATCH /horario/clases/:id`;
  * `DELETE /horario/clases/:id`.
* Los períodos validan nombre, fecha de inicio, fecha de finalización y estado activo.
* Se valida que la fecha de inicio de un período sea anterior a su fecha de finalización.
* La creación o activación de un período desactiva los demás dentro de una transacción, manteniendo un único período activo.
* Las clases programadas validan período, aula, docente, asignatura, proyecto curricular opcional, día de semana, rango horario, grupo e inscritos.
* El día de semana se limita al rango 1 a 6 y las horas admiten los formatos `HH:mm` y `HH:mm:ss`.
* Se valida que todas las entidades relacionadas existan antes de crear o actualizar una clase.
* Se valida que la hora de inicio sea anterior a la hora de fin.
* Se bloquean clases solapadas en la misma aula, período y día; los bloques contiguos sí están permitidos.
* La edición excluye la propia clase al comprobar cruces de horario.
* La consulta de clases permite filtros por aula, período y día, e incluye los datos relacionados necesarios para la vista semanal.
* La eliminación de una clase se bloquea si ya tiene asistencias asociadas, conservando la trazabilidad.
* Se retiraron los DTOs genéricos vacíos de horario y se sustituyeron por DTOs específicos y validados.
* La carga por lote `POST /horario/importar` no se implementó porque el plan la condiciona a que el equipo defina primero el formato de importación.
* Se agregaron pruebas unitarias y E2E de aulas, períodos, activación, clases, validación de rangos y conflictos por solapamiento.

## FUNCIONA

* El CRUD de aulas usa persistencia Prisma y ya no devuelve textos de scaffolding.
* La creación y actualización de aulas validan los datos y rechazan campos no definidos.
* El listado de aulas admite filtros y las consultas incluyen proyecto curricular y software instalado.
* La eliminación de aulas protege su historial operativo.
* Los períodos académicos pueden crearse, consultarse y activarse.
* Solo un período académico queda activo después de crear o activar otro período.
* Las clases programadas pueden crearse, consultarse con filtros, actualizarse y eliminarse.
* Los rangos de fecha y hora se validan antes de acceder a persistencia.
* Las clases no pueden cruzarse en la misma aula, período y día.
* Los errores de duplicado, referencias inexistentes, rangos inválidos y conflictos se convierten en respuestas HTTP claras.
* Las 4 suites unitarias finalizan correctamente: 20 pruebas aprobadas.
* Las 3 suites E2E finalizan correctamente: 7 pruebas aprobadas.
* `npx tsc --noEmit --incremental false`, ESLint y `npm run build` finalizan sin errores.

## NO FUNCIONA

* No se ejecutaron pruebas manuales contra la instancia PostgreSQL configurada; las pruebas automatizadas usan Prisma simulado para no modificar datos locales.
* No existe todavía un formato acordado para importar clases por lote, por lo cual `/horario/importar` permanece pendiente.
* El módulo de horario valida docentes, asignaturas y proyectos existentes, pero no crea ni importa esos catálogos automáticamente porque esa decisión no está definida en el plan.
* La asistencia docente asociada a clases programadas todavía conserva el scaffolding inicial.
* El cálculo dinámico de disponibilidad sigue pendiente.
* Las prácticas libres, préstamos docentes, observaciones restrictivas y panel operativo siguen pendientes.
* La autenticación, el usuario actual y los permisos todavía no están integrados en las operaciones del Core.
* El `ValidationPipe` aún no es global para todo el backend; está aplicado directamente en los controladores implementados.

## NO MODIFICAR

* No crear una tabla permanente para disponibilidad; debe calcularse desde las fuentes operativas.
* No conectar directamente con la base de Gestión de Monitores.
* No retirar las validaciones de DTOs ni los `ParseUUIDPipe` de aulas y horario.
* No permitir la eliminación física de aulas con historial operativo.
* No permitir la eliminación de clases con asistencias asociadas.
* No retirar la transacción que mantiene un solo período académico activo.
* No eliminar ni debilitar la validación de solapamientos de clases.
* No reemplazar `PrismaService` con servicios Prisma privados en los siguientes módulos del Core.
* No implementar `/horario/importar` hasta que se acuerde y documente el formato de carga.
* No modificar las relaciones o enums del Core en Prisma sin revisar las migraciones y el impacto sobre los demás frentes.
* No iniciar el motor de disponibilidad antes de completar la asistencia docente y acordar cómo afecta una ausencia a la disponibilidad.

## SIGUIENTE PASO

* Implementar asistencia docente asociada a clases programadas.
* Crear y validar los contratos:
  * `GET /asistencia-docente?fecha=&aulaId=&estado=`;
  * `POST /asistencia-docente`;
  * `PATCH /asistencia-docente/:id`;
  * `GET /asistencia-docente/clase/:claseId`.
* Permitir registros únicamente sobre clases existentes.
* Evitar múltiples registros activos para una misma clase y bloque operativo.
* Validar los estados `PENDIENTE`, `ASISTIO` y `AUSENTE`.
* Preparar el registro de `registradoPorId` para integrarlo con el usuario autenticado cuando la infraestructura de autenticación esté disponible.
* Preparar la consulta de asistencias pendientes del día para el futuro panel operativo.
* Agregar pruebas unitarias de estados y duplicados, y pruebas E2E de registro y consulta por clase.
* No iniciar disponibilidad, prácticas libres, préstamos docentes, observaciones o panel operativo durante ese siguiente paso.   