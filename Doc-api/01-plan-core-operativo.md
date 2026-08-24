# Plan de implementacion backend - Core operativo

Fecha base: 19/08/2026

Este plan corresponde al frente de Core operativo definido para 3 personas. Cubre los modulos que sostienen la operacion diaria y el calculo de disponibilidad: aulas, horarios, asistencia docente, disponibilidad, practicas libres, prestamos docentes, observaciones que afectan disponibilidad y panel operativo.

El objetivo no es cambiar la arquitectura completa ni introducir patrones academicos artificiales. El objetivo es convertir el esqueleto actual de NestJS en funcionalidad real, con persistencia en Prisma, validaciones, reglas de negocio, pruebas y contratos estables para el frontend.

---

## 0. Reglas del frente

- [X] Trabajar sobre la estructura actual de `backend/src/<modulo>`.
- [X] Mantener los nombres de rutas ya creados cuando sean correctos para no romper al frontend.
- [X] No eliminar controladores ni modulos existentes sin coordinar con los otros frentes.
- [X] Implementar por flujo funcional completo, no por archivos aislados.
- [X] Todo endpoint nuevo o modificado debe tener DTO, validacion, manejo de errores y prueba basica.
- [X] Todo acceso a base de datos debe pasar por `PrismaService`.
- [X] La disponibilidad se calcula en bloques de dos horas al consultar las salas, no se guarda como tabla permanente.
- [X] No integrar directamente con la base de Gestion de Monitores.
- [X] Cada fase debe cerrar con `npm test -- --runInBand` y `npx tsc --noEmit --incremental false`.

---

## 1. Dependencias previas con Plataforma e integracion

Antes de implementar reglas del core, el frente de Plataforma debe entregar:

- [X] `PrismaModule` global o importable.
- [X] `PrismaService` conectado a `DATABASE_URL`.
- [X] `ValidationPipe` global con `whitelist`, `transform` y `forbidNonWhitelisted` si el equipo lo aprueba.
- [X] Filtro global de excepciones o formato comun de error.
- [X] DTOs con `class-validator` disponible.
- [X] Auth basica con usuario autenticado en request.
- [X] Decorador o helper para usuario actual.
- [X] Guard de permisos por modulo, aunque al inicio se pueda usar en modo permisivo.

Mientras esas piezas no existan, este frente puede avanzar con DTOs, servicios puros y tests unitarios usando mocks.

---

## 2. Semana 2 - Administracion de aulas

Objetivo: reemplazar el stub del modulo `aulas` por CRUD real y estable.

### 2.1 Contrato del modulo

- [X] Revisar el modelo `Aula` en `prisma/schema.prisma`.
- [X] Definir respuesta publica de aula sin exponer campos internos innecesarios.
- [X] Documentar endpoints esperados:
  - `POST /aulas`
  - `GET /aulas`
  - `GET /aulas/:id`
  - `PATCH /aulas/:id`
  - `DELETE /aulas/:id` o desactivacion logica si se decide agregar campo `activa`
- [X] Confirmar con frontend los campos minimos para la vista de aulas: codigo, ubicacion, capacidad, estado, caracteristicas, software, historial basico.

### 2.2 DTOs y validaciones

- [X] Completar `CreateAulaDto`.
- [X] Completar `UpdateAulaDto` usando `PartialType`.
- [X] Validar `codigo` como string requerido y unico.
- [X] Validar `ubicacion` como string requerido.
- [X] Validar `capacidad` como entero positivo.
- [X] Validar `estado` contra `EstadoAula`.
- [X] Validar `proyectoCurricularId` como UUID opcional.
- [X] Definir si `caracteristicas` se recibe como JSON libre o estructura controlada.

### 2.3 Servicio con Prisma

- [X] Inyectar `PrismaService` en `AulasService`.
- [X] Implementar `create` con control de codigo duplicado.
- [X] Implementar `findAll` con filtros opcionales por estado, piso/ubicacion y proyecto curricular.
- [X] Implementar `findOne` con `NotFoundException` cuando no exista.
- [X] Implementar `update` validando existencia previa.
- [X] Implementar `remove` con decision explicita:
  - opcion MVP: bloquear eliminacion si tiene clases, prestamos, observaciones o tareas asociadas;
  - opcion estable: convertir a `FUERA_DE_SERVICIO` si no se quiere perder trazabilidad.
- [X] Incluir relaciones necesarias para software e informacion operativa solo cuando el endpoint lo requiera.

### 2.4 Pruebas

- [X] Unit tests de `AulasService` con `PrismaService` mockeado.
- [X] E2E minimo:
  - crear aula;
  - listar aulas;
  - consultar por id;
  - actualizar estado;
  - validar 404 en id inexistente.

Criterio de cierre: el frontend puede reemplazar `rooms.ts` progresivamente con `GET /aulas`.

---

## 3. Semana 2 y 3 - Estructura e importacion de horarios

Objetivo: implementar la base del modulo `horario`, incluyendo periodos, asignaturas, docentes y clases programadas.

### 3.1 Alcance inicial

- [X] Implementar CRUD/consulta de periodos academicos.
- [X] Implementar carga manual o importacion inicial de clases programadas.
- [X] Asociar cada clase con aula, docente, asignatura y periodo.
- [X] Evitar modificar horarios oficiales fuera del sistema; el sistema administra la copia importada.

### 3.2 Contratos propuestos

- [X] `GET /horario/periodos`
- [X] `GET /horario/periodos/:id`
- [X] `POST /horario/periodos`
- [X] `PATCH /horario/periodos/:id/activar`
- [X] `PATCH /horario/periodos/:id`
- [X] `DELETE /horario/periodos/:id`
- [X] `GET /horario/clases?aulaId=&periodoId=&diaSemana=`
- [X] `POST /horario/clases`
- [X] `PATCH /horario/clases/:id`
- [X] `DELETE /horario/clases/:id`
- [X] `POST /horario/importar` para carga por lote cuando el formato este definido.

### 3.3 DTOs

- [X] `CreatePeriodoAcademicoDto`: nombre, fechaInicio, fechaFin, activo.
- [X] `CreateClaseProgramadaDto`: periodoId, aulaId, docenteId, asignaturaId, proyectoCurricularId, diaSemana, horaInicio, horaFin, grupo, inscritos.
- [X] `UpdateClaseProgramadaDto`.
- [X] Validar UUIDs.
- [X] Validar que `diaSemana` este en rango acordado, por ejemplo 1 a 6.
- [X] Validar que `horaInicio < horaFin`.
- [X] Validar que una clase no se cruce con otra clase activa en la misma aula, dia y periodo.

### 3.4 Servicio

- [X] Inyectar `PrismaService` en `HorarioService`.
- [X] Implementar consultas por periodo, aula y dia.
- [X] Implementar upsert o creacion previa de docente/asignatura si el equipo decide importar datos sin catalogos completos.
- [X] Implementar transaccion para carga por lote.
- [X] Devolver errores claros para conflictos de horario.

### 3.5 Pruebas

- [X] Unit tests de validacion de cruces.
- [X] E2E de creacion de periodo y clase.
- [X] E2E de conflicto por solapamiento.

Criterio de cierre: `GET /horario/clases` puede alimentar la vista semanal del frontend.

---

## 4. Semana 4 - Asistencia docente

Objetivo: registrar asistencia real asociada a clases programadas.

### 4.1 Contratos

- [X] `GET /asistencia-docente?fecha=&aulaId=&estado=`
- [X] `POST /asistencia-docente`
- [X] `PATCH /asistencia-docente/:id`
- [X] `GET /asistencia-docente/clase/:claseId`

### 4.2 Reglas

- [X] Solo se registra asistencia sobre una `ClaseProgramada` existente.
- [X] Una clase no debe tener multiples registros activos de asistencia para el mismo bloque operativo, salvo que se defina historial.
- [X] Estado permitido: `PENDIENTE`, `ASISTIO`, `AUSENTE`.
- [X] Guardar `registradoPorId` desde el usuario autenticado cuando auth este disponible.
- [X] Permitir observacion breve.

### 4.3 Implementacion

- [X] Completar DTOs.
- [X] Implementar servicio con Prisma.
- [X] Validar existencia de clase.
- [X] Validar existencia de usuario registrador si se recibe manualmente durante MVP.
- [X] Preparar consulta de asistencias pendientes del dia para el panel operativo.

### 4.4 Pruebas

- [X] Unit tests de estados y duplicados.
- [X] E2E de registro de asistencia.
- [X] E2E de consulta por clase.

Criterio de cierre: disponibilidad puede considerar ausencia docente como senal operativa segun regla aprobada.

---

## 5. Semana 4 - Motor de disponibilidad de aulas

Objetivo: entregar la primera version calculada de disponibilidad.

### 5.1 Fuentes del calculo

- [X] Estado operativo del aula (`Aula.estado`).
- [X] Clases programadas (`ClaseProgramada`).
- [X] Asistencia docente cuando aplique.
- [X] Practicas libres activas.
- [X] Prestamos docentes activos/aprobados.
- [X] Observaciones vigentes de tipo restriccion.
- [X] Tareas que afectan disponibilidad.

### 5.2 Contratos

- [X] `GET /disponibilidad-aulas?fecha=&horaInicio=&horaFin=`
- [X] `GET /disponibilidad-aulas/:aulaId?fecha=&horaInicio=&horaFin=`
- [X] `GET /disponibilidad-aulas/resumen-dia?fecha=`

### 5.3 Modelo de respuesta

- [X] Definir shape estable:
  - aula;
  - estadoCalculado: disponible, ocupada, reservada, mantenimiento, bloqueada;
  - motivo;
  - bloqueActual;
  - siguienteActividad;
  - fuentes que explican el resultado.
- [X] No crear tabla de disponibilidad.
- [X] No mutar datos desde endpoints de disponibilidad.

### 5.4 Servicio

- [X] Crear funciones privadas para consultar cada fuente.
- [X] Normalizar rangos de tiempo.
- [X] Resolver conflictos por prioridad:
  - aula fuera de servicio o mantenimiento;
  - restriccion vigente;
  - clase programada;
  - prestamo docente;
  - practica libre;
  - tarea que afecta disponibilidad;
  - disponible.
- [X] Devolver explicacion legible para frontend y panel operativo.

### 5.5 Pruebas

- [X] Tests unitarios con datasets en memoria/mocks.
- [X] E2E con aula, clase y prestamo docente.
- [X] Caso sin actividades debe retornar disponible.
- [X] Caso aula en mantenimiento debe prevalecer sobre horario.

Criterio de cierre: el frontend puede construir un calendario de disponibilidad sin inferir reglas propias.

---

## 6. Semana 5 - Practicas libres y estudiantes

Objetivo: permitir prestamos de aula a estudiantes para practica libre, respetando disponibilidad y multas.

### 6.1 Contratos

- [X] `GET /practicas-libres?estado=&fecha=&aulaId=`
- [X] `POST /practicas-libres`
- [X] `PATCH /practicas-libres/:id/finalizar`
- [X] `PATCH /practicas-libres/:id/cancelar`
- [X] `GET /practicas-libres/estudiantes/:codigo`

### 6.2 Reglas

- [X] Crear o consultar estudiante por codigo.
- [X] Bloquear practica si el estudiante tiene multa activa.
- [X] Validar que el aula este disponible para el rango solicitado.
- [X] Registrar inicio, fin estimada y fin real.
- [X] Estados iniciales: `ACTIVO`, `DEVUELTO`, `CANCELADO`, `VENCIDO` segun enum disponible.

### 6.3 Implementacion

- [X] Completar DTOs.
- [X] Inyectar `PrismaService`.
- [X] Inyectar o reutilizar logica de `DisponibilidadAulasService` sin generar ciclos de dependencia.
- [X] Implementar transaccion de creacion si se crea estudiante y practica en la misma operacion.
- [X] Implementar finalizacion con `finReal`.

### 6.4 Pruebas

- [X] Unit tests de bloqueo por multa.
- [X] Unit tests de bloqueo por disponibilidad.
- [X] E2E de practica completa: crear, consultar, finalizar.

Criterio de cierre: la accion "Registrar practica libre" del frontend puede conectarse a API real.

---

## 7. Semana 5 - Prestamos docentes de aulas

Objetivo: registrar reservas/prestamos temporales de aulas para docentes.

### 7.1 Contratos

- [X] `GET /prestamos-docentes?estado=&fecha=&docenteId=&aulaId=`
- [X] `POST /prestamos-docentes`
- [X] `PATCH /prestamos-docentes/:id/aprobar`
- [X] `PATCH /prestamos-docentes/:id/cancelar`
- [X] `PATCH /prestamos-docentes/:id/finalizar`

### 7.2 Reglas

- [X] Validar docente existente o crearlo segun decision de importacion.
- [X] Validar aula existente y operativa.
- [X] Validar disponibilidad para el rango.
- [X] Manejar estados del enum `EstadoPrestamo`.
- [X] No permitir aprobar prestamos cruzados.

### 7.3 Implementacion

- [X] DTOs con fecha inicio, fecha fin, docenteId, aulaId y motivo.
- [X] Servicio con Prisma.
- [X] Consulta para panel operativo: proximos prestamos del dia.
- [ ] Auditoria basica si el modulo transversal ya esta listo.

### 7.4 Pruebas

- [X] Unit tests de conflicto de rango.
- [X] E2E de solicitud, aprobacion y cancelacion.

Criterio de cierre: disponibilidad incorpora prestamos docentes como bloqueos reales.

---

## 8. Semana 6 - Observaciones operativas que afectan disponibilidad

Objetivo: permitir novedades y restricciones historicas o vigentes por aula.

### 8.1 Contratos

- [X] `GET /observaciones?aulaId=&tipo=&vigentes=true`
- [X] `POST /observaciones`
- [X] `PATCH /observaciones/:id`
- [X] `DELETE /observaciones/:id` o cierre logico.

### 8.2 Reglas

- [X] `GENERAL` y `NOVEDAD` son informativas.
- [X] `RESTRICCION` afecta disponibilidad mientras este vigente.
- [X] `SEMANAL` debe tener fecha/rango definido si el equipo lo requiere.
- [X] No borrar fisicamente observaciones relevantes para trazabilidad si ya afectaron operacion.

### 8.3 Implementacion

- [X] Completar DTOs.
- [X] Servicio con Prisma.
- [X] Metodo `findRestriccionesVigentes(aulaId, fecha)` para disponibilidad.
- [ ] Registrar usuario creador si se agrega campo al schema o si auditoria lo cubre.

### 8.4 Pruebas

- [X] Unit test de restriccion vigente.
- [X] E2E de creacion y consulta por aula.

Criterio de cierre: disponibilidad puede explicar bloqueos por observaciones.

---

## 9. Semana 6 y 7 - Panel operativo

Objetivo: entregar una vista consolidada para la operacion diaria.

### 9.1 Contratos

- [ ] `GET /panel-operativo/resumen?fecha=`
- [ ] `GET /panel-operativo/aulas?fecha=`
- [ ] `GET /panel-operativo/alertas?fecha=`

### 9.2 Fuentes

- [ ] Disponibilidad calculada.
- [ ] Horarios del dia.
- [ ] Asistencias pendientes o ausencias.
- [ ] Practicas libres activas.
- [ ] Prestamos docentes del dia.
- [ ] Observaciones vigentes.
- [ ] Tareas operativas que afectan disponibilidad.
- [ ] Limpiezas pendientes si el modulo paralelo ya existe.

### 9.3 Implementacion

- [ ] El servicio del panel debe orquestar servicios existentes, no duplicar reglas.
- [ ] Definir DTO de respuesta con metricas y listas.
- [ ] Incluir alertas con severidad: info, advertencia, critica.
- [ ] Mantener consultas paginables cuando las listas crezcan.

### 9.4 Pruebas

- [ ] Unit tests con servicios mockeados.
- [ ] E2E de resumen con al menos un aula ocupada, una libre y una alerta.

Criterio de cierre: el dashboard operativo del frontend puede consumir un unico endpoint de resumen.

---

## 10. Integracion semanal

Al final de cada sprint:

- [ ] Revisar contratos publicados por Plataforma.
- [X] Actualizar `backend/src/MODULES.md` si se agregaron rutas o responsabilidades.
- [ ] Ejecutar migraciones pendientes en entorno local.
- [X] Ejecutar `npm test -- --runInBand`.
- [X] Ejecutar `npx tsc --noEmit --incremental false`.
- [ ] Probar manualmente los endpoints principales con REST client, Postman o curl.
- [X] Reportar rutas listas para que frontend cambie datos mock por datos reales.

---

## 11. Orden recomendado de entrega

1. Aulas.
2. Periodos y clases programadas.
3. Asistencia docente.
4. Disponibilidad calculada.
5. Practicas libres.
6. Prestamos docentes.
7. Observaciones restrictivas.
8. Panel operativo.

Este orden protege la funcionalidad porque cada modulo se apoya en datos ya existentes y evita que disponibilidad o panel operativo se construyan sobre supuestos temporales.
