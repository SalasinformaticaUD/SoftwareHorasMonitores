# Convenciones de API

La API conserva temporalmente las rutas sin prefijo para no romper a los clientes ya
integrados. Todas las rutas se expresan en plural cuando representan colecciones y
usan identificadores UUID como `string`.

Las fechas se envían en ISO 8601. Las colecciones nuevas deben adoptar
`page`, `limit`, `total` e `items` cuando requieran paginación; los filtros se reciben
por query string.

Las respuestas exitosas devuelven directamente el recurso o la colección. Los errores
usan el formato global `{ statusCode, message, error, path, timestamp }`.

| Código | Uso |
| --- | --- |
| 400 | DTO o parámetros inválidos |
| 401 | Autenticación requerida o token inválido |
| 403 | Usuario sin acceso al módulo o permiso |
| 404 | Recurso inexistente |
| 409 | Conflicto de negocio |
| 500 | Error inesperado sin detalles internos |

## Base administrativa

| Recurso | Ruta | Uso |
| --- | --- | --- |
| Dependencias | `/dependencias` | CRUD; no permite borrar dependencias con usuarios. |
| Permisos | `/permisos` | CRUD y consulta del módulo asociado. |
| Roles | `/roles` | CRUD y asignación de permisos mediante `permisoIds`. |
| Usuarios | `/usuarios` | CRUD lógico; `DELETE` desactiva y nunca expone `passwordHash`. |
| Salud | `/health` | Comprobación de disponibilidad de la API. |

Para inicializar catálogos: `npm run prisma:seed`. El comando es idempotente e
inserta las tres dependencias, 15 módulos y seis permisos por módulo.

En `PERMISSIONS_MODE=strict`, los cuatro recursos administrativos requieren acceso
al módulo `ADMINISTRACION`. Sus permisos por operación son:

| Método | Permiso |
| --- | --- |
| `GET` | `ADMINISTRACION_LEER` |
| `POST` | `ADMINISTRACION_CREAR` |
| `PATCH` | `ADMINISTRACION_ACTUALIZAR` |
| `DELETE` | `ADMINISTRACION_ELIMINAR` |

Ejemplo para crear un rol:

```json
{
  "nombre": "ADMINISTRADOR",
  "descripcion": "Gestiona la plataforma",
  "permisoIds": ["uuid-de-un-permiso"]
}
```

Ejemplo de respuesta de login:

```json
{
  "accessToken": "jwt",
  "expiresIn": 28800,
  "tokenType": "Bearer",
  "usuario": { "id": "uuid", "roles": ["ADMINISTRADOR"] },
  "aplicaciones": { "puedeAccederAulas": true, "puedeAccederMonitores": false, "urlMonitores": null }
}
```
