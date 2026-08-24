# Plan de implementacion backend - Modulos paralelos

Fecha base: 19/08/2026

Este plan corresponde al frente de Modulos paralelos definido para 2 personas. Cubre funcionalidades con menor dependencia directa del nucleo operativo, pero que deben respetar las convenciones transversales y conectarse progresivamente con aulas, usuarios, permisos y auditoria.

Los modulos principales de este frente son prestamos audiovisuales, software instalado, multas, credenciales, tareas operativas, limpieza y reportes. Algunos de ellos alimentan disponibilidad o panel operativo cuando el Core ya exponga sus servicios.

---

## 0. Reglas del frente

- [ ] No esperar a que todo el core este terminado para avanzar en modulos independientes.
- [ ] No duplicar reglas de disponibilidad; cuando se necesiten, consumir el servicio del Core.
- [ ] No exponer secretos de credenciales operativas.
- [ ] No eliminar registros historicos importantes.
- [ ] Mantener contratos documentados para que frontend pueda conectar modulo por modulo.
- [ ] Cada fase debe cerrar con `npm test -- --runInBand` y `npx tsc --noEmit --incremental false`.
- [ ] Si una dependencia del Core no esta lista, usar interfaz/servicio mockeable temporal y dejar marcado el punto de reemplazo.

---

## 1. Semana 2 y 3 - Prestamos de equipos audiovisuales

Objetivo: implementar el flujo completo inicial del modulo mas independiente y prioritario para este frente.

### 1.1 Alcance

- [ ] Administrar inventario de equipos audiovisuales.
- [ ] Registrar salida de equipos.
- [ ] Registrar devolucion.
- [ ] Consultar estado de equipos.
- [ ] Consultar historial de prestamos.

### 1.2 Contratos propuestos

- [ ] `GET /prestamos-audiovisuales`
- [ ] `GET /prestamos-audiovisuales/:id`
- [ ] `POST /prestamos-audiovisuales`
- [ ] `PATCH /prestamos-audiovisuales/:id/devolver`
- [ ] `PATCH /prestamos-audiovisuales/:id/cancelar`
- [ ] `GET /prestamos-audiovisuales/equipos`
- [ ] `POST /prestamos-audiovisuales/equipos`
- [ ] `PATCH /prestamos-audiovisuales/equipos/:id`

### 1.3 DTOs

- [X] `CreateEquipoAudiovisualDto`: codigoInventario, nombre, tipo, estado, observacion.
- [X] `UpdateEquipoAudiovisualDto`.
- [X] `CreatePrestamoAudiovisualDto`: docenteId, aulaId, salidaEn, devolucionEstimada, equipos.
- [X] `DevolverPrestamoAudiovisualDto`: devolucionReal, estadoDevolucion por equipo.
- [X] Validar UUIDs, fechas y arreglos no vacios.

### 1.4 Reglas de negocio

- [ ] No prestar equipo en estado distinto a `DISPONIBLE`.
- [ ] Al crear prestamo, cambiar equipos a `PRESTADO`.
- [ ] Al devolver, cambiar equipos a `DISPONIBLE` o `MANTENIMIENTO` segun estado de devolucion.
- [ ] No permitir devolucion de prestamo ya devuelto o cancelado.
- [ ] Si se asocia aula, validar que exista cuando el Core ya exponga `AulasService` o mediante Prisma.
- [ ] Mantener detalle de estado de salida y devolucion.

### 1.5 Implementacion

- [X] Completar DTOs.
- [ ] Implementar servicio con Prisma y transacciones.
- [ ] Usar `DetallePrestamoAudiovisual` para asociar varios equipos a un prestamo.
- [ ] Agregar consultas por estado y fecha.
- [ ] Integrar auditoria cuando Plataforma la entregue.

### 1.6 Pruebas

- [ ] Unit tests de prestamo con equipo disponible.
- [ ] Unit tests de bloqueo con equipo prestado.
- [ ] Unit tests de devolucion.
- [ ] E2E de flujo completo: crear equipo, prestar, devolver.

Criterio de cierre: la accion "Audiovisuales" del frontend puede abrir un flujo conectado a datos reales.

---

## 2. Semana 3 - Software instalado

Objetivo: administrar catalogo de software y relacionarlo con aulas.

### 2.1 Contratos

- [X] `GET /software`
- [X] `GET /software/:id`
- [X] `POST /software`
- [X] `PATCH /software/:id`
- [X] `DELETE /software/:id`
- [X] `GET /software/aulas/:aulaId`
- [X] `POST /software/aulas/:aulaId`
- [X] `DELETE /software/aulas/:aulaId/:softwareId`

### 2.2 DTOs

- [X] `CreateSoftwareDto`: nombre, version, descripcion.
- [X] `UpdateSoftwareDto`.
- [X] `AsignarSoftwareAulaDto`: softwareId o datos para crear y asociar, instaladoEn opcional.
- [X] Validar unicidad por nombre y version.

### 2.3 Reglas

- [X] No duplicar software con mismo nombre y version.
- [X] No duplicar relacion aula-software.
- [X] Permitir consultar software por aula.
- [X] Permitir consultar aulas donde esta instalado un software.
- [X] Eliminar software solo si no esta asociado o definir borrado bloqueado.

### 2.4 Implementacion

- [X] Completar DTOs.
- [X] Servicio con Prisma.
- [X] Metodos de relacion con `AulaSoftware`.
- [X] Preparar endpoint para importacion futura desde archivo, sin implementarlo si no hay formato definido.

### 2.5 Pruebas

- [X] Unit tests de unicidad.
- [ ] E2E de crear software y asignarlo a aula.

Criterio de cierre: la pestana "Software instalado" de aulas puede consumir API real.

---

## 3. Semana 5 - Multas

Objetivo: administrar sanciones que afectan prestamos o practicas libres.

### 3.1 Contratos

- [ ] `GET /multas?estado=&estudianteId=&codigo=`
- [ ] `GET /multas/:id`
- [ ] `POST /multas`
- [ ] `PATCH /multas/:id/cumplir`
- [ ] `PATCH /multas/:id/anular`
- [ ] `GET /multas/motivos`
- [ ] `POST /multas/motivos`

### 3.2 DTOs

- [ ] `CreateMotivoMultaDto`: nombre, descripcion.
- [ ] `CreateMultaDto`: estudianteId o codigoEstudiante, motivoId, descripcion.
- [ ] `UpdateMultaDto` para cambios administrativos permitidos.

### 3.3 Reglas

- [ ] Una multa activa debe bloquear practicas libres segun lo acuerde Core.
- [ ] Cumplir una multa cambia estado a `CUMPLIDA`.
- [ ] Anular una multa requiere descripcion/motivo administrativo.
- [ ] No borrar multas fisicamente.
- [ ] Registrar auditoria cuando este disponible.

### 3.4 Implementacion

- [ ] Completar DTOs.
- [ ] Servicio con Prisma.
- [ ] Metodo `tieneMultaActiva(estudianteId)` exportable para Core.
- [ ] Consultas por codigo de estudiante.

### 3.5 Pruebas

- [ ] Unit test de multa activa.
- [ ] E2E de crear, cumplir y consultar.

Criterio de cierre: practicas libres puede consultar multas sin implementar su propia logica.

---

## 4. Semana 6 - Tareas operativas

Objetivo: gestionar tareas de mantenimiento/operacion y alimentar disponibilidad cuando correspondan.

### 4.1 Contratos

- [ ] `GET /tareas-operativas?estado=&responsableId=&aulaId=&fecha=`
- [ ] `GET /tareas-operativas/:id`
- [ ] `POST /tareas-operativas`
- [ ] `PATCH /tareas-operativas/:id`
- [ ] `PATCH /tareas-operativas/:id/estado`

### 4.2 DTOs

- [ ] `CreateTareasOperativaDto`: aulaId opcional, responsableId opcional, titulo, descripcion, afectaDisponibilidad, inicio, fin.
- [ ] `UpdateTareasOperativaDto`.
- [ ] `CambiarEstadoTareaDto`: estado.

### 4.3 Reglas

- [ ] Si `afectaDisponibilidad` es true, debe tener aula, inicio y fin.
- [ ] No marcar completada una tarea cancelada.
- [ ] No cancelar una tarea completada sin permiso administrativo.
- [ ] Las tareas activas con `afectaDisponibilidad` deben poder consultarse por disponibilidad.

### 4.4 Implementacion

- [ ] Completar DTOs.
- [ ] Servicio con Prisma.
- [ ] Metodo `findTareasQueAfectanDisponibilidad(aulaId, rango)`.
- [ ] Integrar con usuarios/responsables cuando Plataforma entregue usuarios reales.

### 4.5 Pruebas

- [ ] Unit tests de reglas de estado.
- [ ] E2E de crear tarea que afecta disponibilidad.

Criterio de cierre: panel operativo puede mostrar tareas y disponibilidad puede bloquear por tareas.

---

## 5. Semana 6 - Limpieza de aulas

Objetivo: registrar limpiezas, novedades e historial operativo.

### 5.1 Contratos

- [ ] `GET /limpieza-aulas?aulaId=&desde=&hasta=`
- [ ] `GET /limpieza-aulas/:id`
- [ ] `POST /limpieza-aulas`
- [ ] `PATCH /limpieza-aulas/:id`

### 5.2 DTOs

- [ ] `CreateLimpiezaAulaDto`: aulaId, realizadaEn, observacion.
- [ ] `UpdateLimpiezaAulaDto`.

### 5.3 Reglas

- [ ] La limpieza debe estar asociada a un aula existente.
- [ ] Mantener historial.
- [ ] No borrar fisicamente registros de limpieza.
- [ ] Permitir consulta por fecha para reportes.

### 5.4 Implementacion

- [ ] Completar DTOs.
- [ ] Servicio con Prisma.
- [ ] Agregar filtros por aula y rango.
- [ ] Preparar resumen para panel operativo.

### 5.5 Pruebas

- [ ] Unit tests de filtros.
- [ ] E2E de registrar limpieza.

Criterio de cierre: panel operativo y reportes pueden usar historial de limpieza.

---

## 6. Semana 7 - Credenciales operativas

Objetivo: administrar credenciales institucionales de forma segura.

### 6.1 Contratos

- [ ] `GET /credenciales`
- [ ] `GET /credenciales/:id`
- [ ] `POST /credenciales`
- [ ] `PATCH /credenciales/:id`
- [ ] `PATCH /credenciales/:id/estado`
- [ ] `POST /credenciales/:id/accesos`
- [ ] `GET /credenciales/:id/secreto`

### 6.2 Reglas de seguridad

- [ ] Nunca devolver `secretoCifrado` en listados.
- [ ] El secreto solo se revela por endpoint especifico y permiso explicito.
- [ ] Guardar secreto cifrado, no texto plano.
- [ ] Registrar auditoria de consulta de secreto sin guardar el secreto en auditoria.
- [ ] Separar permisos de ver metadata, ver secreto y editar.

### 6.3 Implementacion

- [ ] Definir variable de entorno para clave de cifrado, por ejemplo `CREDENTIALS_ENCRYPTION_KEY`.
- [ ] Crear servicio de cifrado con `crypto` de Node.
- [ ] Completar DTOs.
- [ ] Implementar CRUD de metadata.
- [ ] Implementar gestion de accesos con `AccesoCredencial`.
- [ ] Implementar endpoint de revelado con guard de permisos.

### 6.4 Pruebas

- [ ] Unit test de cifrado/descifrado.
- [ ] Unit test de sanitizacion de respuestas.
- [ ] E2E de crear credencial sin exponer secreto.
- [ ] E2E de revelar secreto solo con permiso.

Criterio de cierre: el modulo puede usarse en piloto sin exponer secretos por accidente.

---

## 7. Semana 8 a 10 - Reportes

Objetivo: generar consultas y formatos operativos sin bloquear el MVP.

### 7.1 Alcance inicial

- [ ] Reporte de uso de aulas por periodo.
- [ ] Reporte de practicas libres.
- [ ] Reporte de prestamos audiovisuales.
- [ ] Reporte de asistencia docente.
- [ ] Reporte de multas.
- [ ] Reporte de limpieza.

### 7.2 Contratos

- [ ] `GET /reportes/uso-aulas?desde=&hasta=`
- [ ] `GET /reportes/practicas-libres?desde=&hasta=`
- [ ] `GET /reportes/prestamos-audiovisuales?desde=&hasta=`
- [ ] `GET /reportes/asistencia-docente?desde=&hasta=`
- [ ] `GET /reportes/multas?desde=&hasta=`
- [ ] `GET /reportes/limpieza?desde=&hasta=`

### 7.3 Formatos

- [ ] Primera entrega: JSON estructurado para frontend.
- [ ] Segunda entrega: CSV si el equipo lo necesita.
- [ ] Tercera entrega: PDF/formatos SIGUD cuando el formato institucional este definido.

### 7.4 Implementacion

- [ ] Completar DTOs de filtros.
- [ ] Servicio con consultas agregadas de Prisma.
- [ ] No duplicar calculos del Core; consumir servicios cuando aplique.
- [ ] Paginacion para reportes detallados.
- [ ] Validacion de rangos de fecha.

### 7.5 Pruebas

- [ ] Unit tests de filtros.
- [ ] E2E de un reporte JSON por modulo implementado.

Criterio de cierre: se pueden generar informes operativos basicos para la prueba piloto.

---

## 8. Integracion con Core y Plataforma

Al final de cada sprint:

- [ ] Confirmar que `PrismaModule` y guards transversales siguen funcionando.
- [ ] Confirmar que no se rompio ningun endpoint del Core.
- [ ] Publicar contratos listos para frontend.
- [ ] Actualizar `backend/src/MODULES.md` si se agregan rutas.
- [ ] Revisar con Core los metodos compartidos:
  - multas activas;
  - tareas que afectan disponibilidad;
  - software por aula;
  - prestamos audiovisuales por aula/dia;
  - limpieza para panel.
- [ ] Ejecutar pruebas completas del backend.

---

## 9. Orden recomendado de entrega

1. Prestamos audiovisuales e inventario de equipos.
2. Software instalado y asociacion con aulas.
3. Multas y motivos.
4. Tareas operativas.
5. Limpieza de aulas.
6. Credenciales operativas seguras.
7. Reportes JSON.
8. Exportaciones y formatos institucionales.

Este orden permite avanzar en paralelo sin invadir el motor de disponibilidad, pero deja preparados los puntos donde esos modulos alimentan el panel operativo y los reportes.
