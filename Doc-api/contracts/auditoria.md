# Auditoría

El servicio `AuditoriaService.registrar` guarda la trazabilidad de operaciones
críticas. Cada registro contiene `usuarioId`, `entidad`, `entidadId`, `accion`,
`datosPrevios`, `datosNuevos` y fecha de creación.

Las acciones válidas son `CREATE`, `UPDATE`, `DELETE`, `DISABLE`, `APPROVE`,
`CANCEL` y `LOGIN`. Antes de guardar, los nombres de campo que contienen
`password`, `contrasena`, `secret`, `token` o `authorization` se reemplazan por
`[REDACTED]`.

La consulta está disponible en `GET /auditoria` y acepta `entidad`, `entidadId`,
`usuarioId`, `desde` y `hasta`. Requiere el módulo y permiso
`ADMINISTRACION_LEER` cuando `PERMISSIONS_MODE=strict`.

Actualmente se registra de forma manual en dependencias, roles, permisos, usuarios,
aulas y préstamos docentes. Los módulos que aún son stubs deben integrarse cuando
sus servicios reales estén implementados.
