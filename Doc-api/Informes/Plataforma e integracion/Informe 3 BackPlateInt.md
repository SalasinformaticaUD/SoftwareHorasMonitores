# Informe 3 - Integración de Monitores con Plataforma

FECHA: 22/08/2026  
AUTORES: Esteban Bautista

## OBJETIVO DE LA JORNADA

Completar la preparación de la API de Gestión de Monitores para su consumo desde la plataforma general de Software Monitorías, retirar el frontend local de esta rama y dejar documentado el flujo técnico y de pruebas de integración.

## AVANCES REALIZADOS

### Integración entre Plataforma (Aulas) y Monitores

* Se mantuvo la separación definida en el plan: Plataforma/Aulas y Monitores conservan bases de datos independientes y se integran únicamente por HTTP. No se implementaron consultas cruzadas a las bases de datos.
* Se completó en Aulas el endpoint interno `POST /integraciones/monitores/usuarios` para crear o vincular la identidad central solicitada desde Monitores.
* El endpoint de aprovisionamiento está protegido con el encabezado de servicio `X-Monitores-Service-Token` y valida la configuración antes de aceptar solicitudes.
* El aprovisionamiento es idempotente: si ya existe el usuario con el mismo nombre de usuario o correo, devuelve su UUID central sin crear un duplicado. Si los dos datos identifican usuarios distintos, responde con conflicto para evitar vínculos incorrectos.
* Los usuarios creados automáticamente en Aulas quedan inicialmente inactivos, sin roles asignados y con una contraseña aleatoria no expuesta. Un administrador de la plataforma debe activarlos y asignar sus permisos según el proceso institucional.
* Se añadió en Monitores el cliente HTTP que consume dicho endpoint de Aulas y valida que la respuesta contenga un UUID válido.
* Se añadió el endpoint de Monitores `POST /api/v1/monitors/provision/`. Este crea el vínculo de identidad central, guarda el UUID en `Monitor.usuario_externo_id` y lo replica en el usuario local asociado. Una repetición con la misma identidad no crea otro monitor.
* Se incorporó `usuario_externo_id` al modelo de usuario local de Monitores, junto con su migración, para permitir validar la identidad recibida desde Plataforma.
* Se implementó autenticación JWT de Plataforma en Monitores. Monitores valida tokens HS256 emitidos por Aulas, verifica expiración y exige que el `sub` del token esté vinculado a un usuario local activo.
* Se añadieron `GET /api/v1/platform/me/` para consultar la identidad local vinculada y CORS configurable mediante `CORS_ALLOWED_ORIGINS` para el frontend general.
* Se conservaron los contratos de consulta que consume Aulas: `GET /health` y `GET /usuarios/{usuarioExternoId}`. El segundo devuelve el vínculo del monitor o `404` si no existe, que es el comportamiento acordado.

### Retiro del frontend local

* Se retiró el frontend renderizado por Django de esta rama `Api-gestion-monitores`: plantillas, vistas web, formularios, administración web y rutas asociadas.
* Se eliminaron la configuración de sesiones, plantillas, archivos estáticos, WhiteNoise y las rutas de login web local que ya no corresponden a la arquitectura objetivo.
* La aplicación de Monitores queda orientada exclusivamente a API. El frontend de la plataforma general debe consumirla mediante HTTP y autenticarse primero contra Aulas.
* Este retiro fue realizado únicamente en la rama de integración; no modifica las ramas `main` ni `version-2.0`, que conservan el frontend de referencia para el equipo correspondiente.

### Documentación

* Se amplió `docs/integracion-plataforma.md` con la arquitectura, variables de entorno, contratos HTTP, ciclo de vida Usuario--Monitor, autenticación, CORS, aprovisionamiento y secuencia de consumo desde el frontend general.
* Se actualizó el README para reflejar que el proyecto es API-first y que la autenticación central proviene de Plataforma/Aulas.
* Se documentó el punto 8 del plan de Plataforma e Integración, incluyendo la secuencia recomendada de validación manual y los criterios de endurecimiento aplicables a este alcance.

## FLUJO FINAL PROPUESTO

1. El usuario inicia sesión en Plataforma/Aulas mediante `POST /auth/login`.
2. Aulas devuelve el JWT y determina si el usuario tiene acceso al módulo MONITORES.
3. El frontend general guarda el token de forma segura y lo envía como `Authorization: Bearer <token>` al consumir Monitores.
4. Monitores valida la firma y expiración del JWT, busca el `usuario_externo_id` local y permite el acceso solo si el usuario vinculado está activo.
5. Para registrar un monitor, un administrador autorizado llama a `POST /api/v1/monitors/provision/` en Monitores.
6. Monitores solicita a Aulas la creación o vinculación idempotente del usuario central y guarda el UUID recibido en ambos lados de su modelo local.
7. Aulas puede consultar posteriormente `GET /usuarios/{usuarioExternoId}` en Monitores para confirmar que el vínculo con el monitor existe.
8. El frontend general consume los recursos operativos de Monitores: monitores, horarios, asistencias, sesiones, anotaciones, reportes y notificaciones.

## VALIDACIONES EJECUTADAS

### Backend de Monitores

* `python manage.py check`: aprobado.
* `python manage.py makemigrations --check --dry-run`: aprobado; no se detectaron migraciones pendientes.
* Suite restante orientada a API/backend: **58 pruebas aprobadas**.
* Se añadieron pruebas para autenticación JWT de Plataforma, CORS y aprovisionamiento idempotente del monitor.

### Backend de Plataforma/Aulas

* `npx tsc --noEmit --incremental false`: aprobado.
* `npm test -- --runInBand`: **81 pruebas aprobadas**.
* `npm run test:e2e -- --runInBand`: **39 pruebas aprobadas**.
* `npm run build` quedó bloqueado por un error de permisos de Windows al limpiar el directorio `dist` (`EPERM`); no fue un error de compilación TypeScript. Debe repetirse tras cerrar procesos que estén usando esa carpeta o eliminarla de forma controlada.

## VALIDACIÓN MANUAL PENDIENTE EN POSTMAN

Las pruebas automatizadas y de contrato están listas, pero el smoke test entre ambos servicios aún debe ejecutarse con los dos backends encendidos y sus variables de entorno reales. La colección debe comprobar, como mínimo:

1. Login en Aulas y obtención de `accessToken`.
2. Consulta `GET /health` de Monitores desde la configuración de integración de Aulas.
3. Consulta protegida `GET /api/v1/platform/me/` en Monitores con el JWT recibido.
4. Aprovisionamiento `POST /api/v1/monitors/provision/` con un usuario nuevo.
5. Repetición de la misma solicitud y confirmación de que no se crean usuarios ni monitores duplicados.
6. Consulta en Aulas de `GET /integraciones/monitores/usuarios/{uuid}` y confirmación del vínculo devuelto por Monitores.
7. Prueba de un token inválido, expirado o no vinculado, esperando rechazo `401`.
8. Prueba sin `X-Monitores-Service-Token` o con uno incorrecto en el endpoint interno de Aulas, esperando rechazo `401`.
9. Recorrido funcional de los endpoints operativos de Monitores que usará el frontend general.

Las rutas antiguas de login local bajo `/api/v1/auth/login/` ya no forman parte del flujo y no deben incluirse en la colección nueva.

## PENDIENTES Y DECISIONES ABIERTAS

* Ejecutar y registrar el smoke test real en Postman, con Aulas y Monitores comunicándose por URL y secretos de entorno reales. Hasta entonces no debe declararse cerrada la integración en vivo.
* Configurar de forma segura en cada entorno: `MONITORES_API_URL`, `PLATFORM_API_URL`, `MONITORES_SERVICE_TOKEN`, `PLATFORM_JWT_SECRET` y `CORS_ALLOWED_ORIGINS`. Los secretos no deben versionarse ni compartirse con el frontend.
* Activar los usuarios centrales generados por aprovisionamiento y asignarles los roles/permisos de Aulas que correspondan al módulo MONITORES.
* Alinear la autorización fina: actualmente el aprovisionamiento en Monitores exige que el usuario local vinculado tenga rol administrador. Si se desea usar directamente los permisos del JWT central (por ejemplo `MONITORES_CREAR`), debe implementarse el mapeo y validación explícitos de esos claims.
* Definir el manejo institucional de cambios de correo o nombre de usuario, desactivaciones y eliminación lógica. La regla de negocio acordada se conserva: eliminar un Usuario no debe eliminar automáticamente el Monitor, ni eliminar un Monitor debe eliminar automáticamente el Usuario; se debe conservar el histórico y el vínculo externo cuando aplique.
* Revisar si las funcionalidades que solo existían en pantallas web retiradas necesitan una ruta API equivalente antes de que el frontend general las implemente.
* Repetir `npm run build` de Aulas cuando el bloqueo del directorio `dist` haya sido liberado.
* Revisar de forma global, con los responsables de Aulas, los puntos del checklist 8 que exceden esta integración (módulos, DTOs, seeds y auditoría de todos los dominios), pues este informe solo valida el alcance intervenido.

## ESTADO ACTUAL

La API de Monitores quedó preparada para ser consumida desde el frontend general y para integrarse con la identidad central de Aulas sin compartir base de datos. El código y la documentación cubren el contrato técnico; falta la prueba manual extremo a extremo con la configuración real y el cierre de las decisiones operativas de permisos, activación y ciclo de vida de usuarios.
