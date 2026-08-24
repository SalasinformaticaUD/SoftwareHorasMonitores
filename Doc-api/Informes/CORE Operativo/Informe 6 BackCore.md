# Informe 5 - BackCore

FECHA: 21/08/2026  
MONITOR: Ivan Felipe Prado Blanco 10:00am - 2:00pm

## AVANCES

* Se continuó el recorrido de `backend/docs/01-plan-core-operativo.md`, respetando la ruta de desarrollo del Informe 3 y sin utilizar el Informe 4 como fuente de nuevas decisiones funcionales.
* Se verificó que los pendientes documentados en el Informe 3 ya fueron atendidos: `ValidationPipe` global, filtro uniforme de excepciones, resumen diario de disponibilidad, rango operativo configurable, cálculo de `siguienteActividad` y escenario E2E de prioridad entre clase y préstamo docente.
* Se implementó autenticación básica centralizada:
  * `POST /auth/login`;
  * `GET /auth/me`;
  * contraseñas protegidas mediante hash `scrypt`;
  * tokens firmados con expiración;
  * usuario autenticado disponible en la petición;
  * decorador `CurrentUser`;
  * guard global de autenticación;
  * guard de permisos por módulo con modos permisivo y estricto.
* Se confirmó y publicó el contrato mínimo de aulas requerido por frontend: código, ubicación, piso, capacidad, estado, características, proyecto curricular, software e historial operativo básico.
* Se creó el tipo de respuesta de aulas para frontend y se documentó el contrato en `backend/docs/contracts/aulas.md`.
* Se implementó `POST /horario/importar` con los formatos JSON versionados:
  * `JSON_V1` para catálogos existentes mediante UUID;
  * `JSON_V2` para permitir docente y asignatura embebidos;
  * validación de hasta 500 filas;
  * identificación de la fila que produce un error;
  * control de cruces de horario;
  * ejecución transaccional con reversión completa ante conflicto.
* Se implementó creación o actualización de docentes por documento y asignaturas por código durante importaciones `JSON_V2`, evitando depender de catálogos previamente completos.
* Se completó el CRUD literal de periodos académicos:
  * `GET /horario/periodos/:id`;
  * `PATCH /horario/periodos/:id`;
  * `DELETE /horario/periodos/:id`;
  * validación del rango de fechas;
  * conservación de un único periodo activo;
  * bloqueo de eliminación cuando existen clases asociadas.
* Se completó el módulo de observaciones operativas con consulta filtrada, creación, actualización, cierre lógico, restricciones vigentes reutilizables por disponibilidad y pruebas unitarias y E2E.
* El registro de asistencia docente ahora exige autenticación y guarda `registradoPorId` exclusivamente desde `CurrentUser`; el cliente no puede enviar ni modificar ese identificador.
* Se reemplazó la prueba E2E simulada de prácticas libres por un flujo que utiliza el módulo y servicio reales, manteniendo estado en memoria únicamente en las fronteras de Prisma y disponibilidad.
* El E2E de prácticas libres comprueba el flujo completo de creación, consulta, finalización y consulta posterior de la transición `ACTIVO` a `DEVUELTO`.
* Se agregó validación del código estudiantil en `GET /practicas-libres/estudiantes/:codigo`, con casos exitoso, inválido y estudiante inexistente.
* Se agregó cobertura específica para `PATCH /practicas-libres/:id/cancelar`, incluyendo transición a `CANCELADO`, registro de `finReal` y consulta posterior.
* Se implementó la transición persistida a `VENCIDO` cuando una práctica activa supera `finEstimada` sin registrar `finReal`.
* Una práctica vencida puede finalizarse como devolución tardía y pasar a `DEVUELTO`, pero no puede cancelarse.
* Se formalizó el contrato público de disponibilidad mediante tipos para aula, bloque, estado calculado, fuentes, siguiente actividad, respuesta individual y resumen diario.
* Se publicó `backend/docs/contracts/disponibilidad-aulas.md` y se amplió el E2E para verificar el shape completo de la respuesta.
* Se realizaron dos barridos completos de los bloques 0 a 6. El primero permitió identificar y corregir cinco brechas internas del plan; el segundo contrastó el resultado contra el Informe 3 y el Documento de Ingeniería de Software.
* El segundo barrido confirmó que las 124 casillas explícitas de los bloques 0 a 6 están marcadas con `[X]` y cuentan con implementación verificable.
* El contraste con los requerimientos funcionales detallados identificó seis recomendaciones nuevas que amplían el alcance incremental del plan y deben ser atendidas por el siguiente monitor.

## FUNCIONA

* Auth permite iniciar sesión, recuperar el usuario actual y aplicar permisos por módulo desde backend.
* Aulas expone un contrato estable con información general, software e historial básico.
* Periodos académicos dispone de creación, listado, consulta individual, actualización, activación exclusiva y eliminación segura.
* Horarios permite carga manual e importación JSON transaccional con catálogos existentes o embebidos.
* La asistencia docente conserva la autoría mediante el usuario autenticado y evita suplantación desde el body.
* Observaciones restrictivas alimentan el motor de disponibilidad sin duplicar reglas.
* Disponibilidad continúa siendo de solo lectura, trabaja en bloques exactos de dos horas, conserva la prioridad definida y no persiste resultados.
* El resumen diario, la siguiente actividad y el contrato tipado de disponibilidad están disponibles para integración.
* Prácticas libres crea o consulta estudiantes, valida multas y disponibilidad, registra devoluciones, cancelaciones y vencimientos.
* Los E2E de prácticas libres utilizan el servicio real y comprueban cambios de estado entre peticiones.
* Las 11 suites unitarias finalizan correctamente: 71 pruebas aprobadas.
* Las 9 suites E2E finalizan correctamente: 34 pruebas aprobadas.
* TypeScript, ESLint sobre los archivos modificados, `npm run build` y `git diff --check` finalizan sin errores.

## NO FUNCIONA

* La importación de horarios todavía recibe JSON y no procesa directamente el archivo oficial de Microsoft Excel requerido por RF-001, RF-002, RNF-004, RNF-021 y RNF-025.
* La importación no filtra automáticamente aulas externas, no reemplaza una versión anterior del mismo periodo y no informa cantidades separadas de registros actualizados y rechazados.
* Aulas no modela explícitamente año de adquisición, marca, modelo, renovación tecnológica ni estado pendiente de intervención; actualmente parte de esa información solo podría almacenarse como JSON libre.
* Un aula solo puede asociarse directamente con un proyecto curricular y los filtros no incluyen código ni capacidad.
* Disponibilidad no permite filtrar o sugerir aulas por software, capacidad o características, ni ofrece un historial derivado de cambios de disponibilidad.
* La ausencia docente no libera automáticamente el aula. Esta conducta respeta el Informe 3, pero RF-025 y RF-028 requieren una decisión operativa formal sobre el tiempo de espera y la liberación.
* Prácticas libres no registra software solicitado, capacidad requerida, funcionario responsable ni observaciones; tampoco expone duración, tiempo transcurrido o tiempo disponible hasta la siguiente actividad.
* La búsqueda de estudiantes se realiza por código, pero no por documento de identificación.
* Auth y permisos pueden operar en modo permisivo durante desarrollo; aún falta cerrar sesión por inactividad y configurar CORS para orígenes autorizados antes de considerar cumplida la seguridad final.
* El frontend de aulas continúa consumiendo datos simulados desde `rooms.ts`; el contrato está publicado, pero todavía no se reemplazó por la API real.
* Las pruebas automatizadas continúan sustituyendo Prisma y no validan los flujos contra una base PostgreSQL exclusiva y aislada para pruebas.
* Los cambios de esta sesión están en el árbol de trabajo de `main`; todavía no puede acreditarse integración mediante rama funcional, commit, revisión por otro integrante o aprobación para la rama estable.

## NO MODIFICAR

* No crear una tabla, modelo o migración para persistir la disponibilidad calculada.
* No agregar `POST`, `PATCH` o `DELETE` al controlador de disponibilidad.
* No aceptar bloques distintos de dos horas ni bloques que comiencen en una hora impar mientras esta regla continúe vigente.
* No cambiar la prioridad del motor de disponibilidad sin aprobación del equipo responsable.
* No liberar automáticamente un aula por ausencia docente hasta acordar formalmente la regla y el tiempo de espera.
* No duplicar la lógica de disponibilidad dentro de prácticas libres, préstamos docentes o panel operativo.
* No permitir que el cliente envíe o modifique `registradoPorId` en asistencia docente.
* No retirar la restricción única `(claseId, fecha)` ni permitir que asistencia cambie la clase o fecha mediante `PATCH`.
* No crear clientes Prisma privados por módulo; todo acceso debe utilizar `PrismaService`.
* No acceder directamente a la base de datos de Gestión de Monitores; cualquier integración debe realizarse mediante API.
* No ejecutar pruebas automatizadas destructivas contra la base de desarrollo; preparar primero una base PostgreSQL exclusiva para pruebas.
* No modificar los Informes 1, 2, 3 o 4 para incorporar los avances de esta sesión.

## SIGUIENTE PASO

El siguiente monitor debe trabajar inmediatamente en estas seis recomendaciones, respetando el orden indicado:

1. **Importación oficial de horarios.** Implementar lectura de Microsoft Excel, validación de estructura, filtrado de registros correspondientes a las Aulas de Software, reemplazo autorizado de la versión anterior del mismo periodo y resumen con procesados, creados, actualizados y rechazados. Asegurar que los procesos operativos utilicen únicamente el periodo activo.
2. **Completar el modelo y filtros de aulas.** Definir campos controlados para año de adquisición, marca, modelo, renovación tecnológica y estado pendiente de intervención; acordar la asociación de múltiples proyectos curriculares y agregar filtros por código y capacidad sin romper el contrato público existente.
3. **Extender disponibilidad.** Incorporar filtros por software, capacidad y características, sugerencia ordenada de aulas y una consulta histórica derivada de las fuentes operativas, sin crear una tabla de disponibilidad ni alterar la prioridad definida.
4. **Resolver la regla de ausencia docente.** Acordar con el equipo responsable el tiempo de espera y si `AUSENTE` libera el aula. Documentar la decisión y solo después ajustar RF-025/RF-028, servicio y pruebas. Hasta entonces conservar la conducta actual del Informe 3.
5. **Completar prácticas libres según RF-031 a RF-048.** Agregar búsqueda por documento, software solicitado, capacidad requerida, funcionario responsable, observaciones, duración, tiempo transcurrido y validación contra la siguiente actividad programada. Reutilizar disponibilidad y software en lugar de duplicar consultas.
6. **Cerrar seguridad e integración.** Preparar modo estricto para autenticación y permisos, inactividad de sesión y CORS; conectar frontend con las APIs reales; crear una base PostgreSQL aislada para E2E; trabajar en rama funcional y solicitar revisión antes de integrar a la rama estable.

Comenzar por la recomendación 1. No avanzar simultáneamente sobre las seis si esto impide cerrar un flujo completo con DTO, validaciones, persistencia, manejo de errores, contrato y pruebas.
