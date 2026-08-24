# Integración API-first con la Plataforma de Monitorías

## Arquitectura

Gestión de Monitores conserva su base de datos y reglas de horas, asistencia,
horarios y novedades. Gestión de Aulas es la fuente de identidad, autenticación y
permisos. Las bases no se consultan entre sí: la comunicación es HTTP.

El frontend general no inicia sesión en Monitores. Inicia sesión en Gestión de Aulas,
obtiene un JWT Bearer y lo reenvía a Monitores. La interfaz HTML heredada queda
retirada de esta rama API; el frontend general es el único cliente.

### Responsabilidad de cada base de datos

No existe una única base de datos con todos los dominios, y no debe crearse una.
La plataforma usa dos bases PostgreSQL separadas:

| Base | Propietario | Datos que administra |
| --- | --- | --- |
| Base general de Gestión de Aulas | Backend principal | Usuarios, contraseñas, estado de cuenta, roles, permisos, dependencias, aulas y módulos generales. |
| Base de Gestión de Monitores | API de Monitores | Monitores, horarios, asistencia, horas, sesiones, anotaciones, reportes y novedades. |

La relación entre ambas es lógica: se guarda el UUID del usuario de Aulas, nunca
una llave foránea ni una consulta SQL entre bases. Aulas no replica datos operativos
de Monitores; Monitores no debe ser fuente de contraseñas, roles o permisos.

## Configuración

| Variable | Uso |
| --- | --- |
| `PLATFORM_JWT_SECRET` | Mismo valor que `JWT_SECRET` en Gestión de Aulas; valida JWT HS256. |
| `FRONTEND_URL` | Orígenes permitidos del frontend general, separados por coma. |
| `PLATFORM_API_URL` | URL del backend de Gestión de Aulas, por ejemplo `http://localhost:3000`. |
| `MONITORES_SERVICE_TOKEN` | Secreto de servidor compartido con Aulas para provisionar identidades. Nunca llega al navegador. |
| `PLATFORM_API_TIMEOUT_SECONDS` | Tiempo máximo de la llamada de provisión; por defecto `5`. |

El JWT debe tener firma HS256, `sub` UUID y `exp` vigente. Si el `sub` no está
vinculado a un perfil local activo, Monitores devuelve `401`.

## Flujo del frontend general

```text
Frontend -> POST Aulas /auth/login
         <- accessToken Bearer + aplicaciones.puedeAccederMonitores

Frontend -> GET Monitores /api/v1/platform/me/
            Authorization: Bearer <accessToken>
         <- perfil local vinculado + contexto de plataforma

Frontend -> APIs /api/v1/* con el mismo Bearer token
         <- datos limitados por el rol y dependencia locales
```

Monitores valida el token sin consultar la base de Aulas, después busca el perfil
local cuyo `usuario_externo_id` coincide con el `sub`.

## Ciclo de vida de usuarios y monitores

Un usuario y un monitor no son exactamente el mismo recurso. El usuario pertenece a
la plataforma general; el monitor es un perfil funcional de Gestión de Monitores.

| Operación | Resultado esperado |
| --- | --- |
| Crear usuario en Aulas | Crea una identidad central; no crea un monitor automáticamente. |
| Crear monitor | Crea o reutiliza la identidad central, crea el perfil Monitor y guarda su UUID. |
| Desactivar usuario vinculado a un monitor | Bloquea el acceso; conserva el monitor y todo su historial de asistencia y horas. |
| Desactivar monitor | Conserva el usuario central; Aulas puede retirarle los permisos del módulo `MONITORES`. |
| Eliminar físicamente usuario o monitor | No se recomienda: se debe conservar trazabilidad mediante desactivación lógica. |

Por tanto, un usuario puede no ser monitor, pero todo monitor debe tener una identidad
central vinculada. Un usuario central puede conservar su identidad después de dejar
de ser monitor.

### Estado actual y ajuste pendiente

La integración nueva usa Aulas como fuente de autenticación. Sin embargo, Monitores
mantiene temporalmente `users.User` como perfil operativo heredado para aplicar el
alcance local por dependencia. Ese perfil debe tratarse como espejo: sin contraseña
propia ni autoridad sobre roles/permisos. La migración gradual debe retirar el uso de
credenciales locales cuando el frontend general esté completamente en producción.

El endpoint CRUD heredado `DELETE /api/v1/monitors/{id}/` todavía realiza borrado
físico. Antes de habilitar esa acción desde el frontend general debe cambiarse por
una desactivación lógica para cumplir el ciclo de vida anterior.

## Vínculo de identidades

| Campo | Propósito |
| --- | --- |
| `users.User.usuario_externo_id` | Resuelve el JWT al perfil operativo local. |
| `monitors.Monitor.usuario_externo_id` | Relación usuario central-monitor que consulta Aulas. |

Para migrar un perfil existente:

```powershell
python manage.py link_platform_identity `
  --local-username leader.physics `
  --platform-user-id <uuid-de-usuarios-en-aulas>
```

El comando también vincula el monitor asociado; se puede indicar `--monitor-id`.

## Endpoints entre backends

Gestión de Aulas los consume mediante `MONITORES_API_URL`:

| Método y ruta | Respuesta | Uso |
| --- | --- | --- |
| `GET /health` | `{ "status": "ok", "checks": { "database": "ok" } }` | Disponibilidad. |
| `GET /usuarios/{usuarioExternoId}` | `{ id, usuarioExternoId, nombre, estado }` | Resolver monitor asociado. |

`GET /usuarios/{usuarioExternoId}` devuelve `404` si no existe vínculo; esto no es
un fallo de integración.

## Endpoints para el frontend general

Todas las rutas funcionales requieren `Authorization: Bearer <accessToken>`. La
carga de asistencia usa `multipart/form-data`; las demás, JSON.

| Área | Ruta base | Operaciones |
| --- | --- | --- |
| Contexto | `GET /api/v1/platform/me/` | Perfil local vinculado y claims seguros. |
| Monitores | `/api/v1/monitors/` | CRUD de monitores. |
| Horarios | `/api/v1/schedules/` | CRUD y `/exceptions/`. |
| Asistencia | `/api/v1/attendance/imports/` | Carga/consulta y conciliación pendiente. |
| Sesiones | `/api/v1/sessions/` | Consulta y `/{id}/review-overtime/`. |
| Anotaciones | `/api/v1/annotations/` | CRUD. |
| Reportes | `/api/v1/reports/dashboard/`, `/generate/`, `/snapshots/` | Panel y snapshots. |
| Notificaciones | `/api/v1/notifications/` | Consulta y `/{id}/mark-read/`. |

OpenAPI se expone en `GET /api/schema/` y Swagger en `GET /api/docs/`.

```javascript
const response = await fetch(`${MONITORES_API_URL}/api/v1/reports/dashboard/`, {
  headers: { Authorization: `Bearer ${accessToken}` },
});
const dashboard = await response.json();
```

### Crear un monitor desde el frontend general

`POST /api/v1/monitors/provision/` es la ruta para altas nuevas. Requiere el JWT
del administrador central y no expone el secreto de servicio:

```json
{
  "full_name": "Ana Torres",
  "codigo_estudiante": "20260001",
  "email": "ana.torres@udistrital.edu.co",
  "username": "ana.torres",
  "department": "physics",
  "numero_documento": "123456789",
  "proyecto_curricular": "licenciatura_fisica",
  "telefono": "3001234567"
}
```

Monitores llama internamente a Aulas, recibe el UUID central y crea el perfil local
vinculado. La respuesta es el monitor creado; repetir la misma solicitud para un UUID
ya vinculado devuelve ese monitor sin duplicarlo.

## Provisión interna Monitores → Aulas

Monitores consume este endpoint privado de Aulas; el frontend nunca debe llamarlo:

| Método y ruta | Header requerido | Cuerpo |
| --- | --- | --- |
| `POST /integraciones/monitores/usuarios` | `X-Monitores-Service-Token: <MONITORES_SERVICE_TOKEN>` | `nombreCompleto`, `nombreUsuario`, `correo`, y opcionalmente `dependenciaId`. |

La operación es idempotente por `nombreUsuario` o `correo`. Devuelve:

```json
{ "id": "uuid", "creado": true, "estado": "INACTIVA" }
```

Un usuario nuevo queda `INACTIVA` y con contraseña aleatoria no utilizable: el
administrador de Aulas debe asignarle contraseña, activarlo y otorgarle permisos del
módulo `MONITORES` antes de que pueda iniciar sesión en el frontend general. Si ya
existía, Aulas conserva sus datos y devuelve su UUID con `creado: false`.

## Administración de identidades existentes

`link_platform_identity` sigue disponible para migrar perfiles creados antes de esta
integración. Las altas nuevas deben usar `/api/v1/monitors/provision/`.

## Validación del punto 8 del plan de Plataforma e Integración

El punto 8 corresponde principalmente al backend central NestJS. Para la integración
actual, la validación queda así:

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| Rutas protegidas con guard | Cumplido para el flujo nuevo | Aulas usa guards globales; Monitores valida JWT y permisos DRF. |
| CORS para frontend local | Cumplido | `FRONTEND_URL` restringe los orígenes permitidos. |
| Health endpoint | Cumplido | `GET /health` en ambos servicios. |
| Migraciones | Cumplido | Monitores no tiene migraciones pendientes. |
| Seeds de permisos y administrador | Cumplido en Aulas | `prisma:seed` crea `MONITORES`, permisos y administrador. |
| Pruebas unitarias | Cumplido en Aulas | 81 pruebas aprobadas. |
| Pruebas e2e | Cumplido en Aulas | 39 pruebas aprobadas, incluida la provisión. |
| Tipos TypeScript | Cumplido en Aulas | `npx tsc --noEmit --incremental false`. |
| Pruebas API de Monitores | Cumplido | 143 pruebas aprobadas antes del retiro de pruebas web obsoletas. |
| Smoke de negocio completo | Pendiente de Postman | Login, aulas, horarios, disponibilidad, préstamos y panel reales. |
| Documentación | Cumplido | Este documento y los contratos de `Doc-api/contracts`. |

### Secuencia recomendada para Postman

Las colecciones antiguas que comienzan con `/api/v1/auth/login/` pertenecen al
frontend local retirado y no deben usarse para este flujo. El login debe ejecutarse
contra Aulas.

1. Ejecutar `POST {AULAS_API_URL}/auth/login` y guardar `accessToken`.
2. Verificar `aplicaciones.puedeAccederMonitores`.
3. Ejecutar `GET {MONITORES_API_URL}/health`.
4. Ejecutar `GET {MONITORES_API_URL}/api/v1/platform/me/` con el Bearer.
5. Crear un monitor con `POST /api/v1/monitors/provision/` usando un administrador
   central con permiso `MONITORES_CREAR`.
6. Repetir la provisión y confirmar que no se duplica.
7. Consultar `GET /usuarios/{usuarioExternoId}` desde Aulas.
8. Probar monitor, horario, importación, sesión, anotación, dashboard y notificación.

El secreto `MONITORES_SERVICE_TOKEN` solo lo usa el backend de Monitores al llamar a
`POST /integraciones/monitores/usuarios`; nunca debe configurarse en Postman ni en el
frontend.
