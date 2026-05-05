# Flujo de carga de horarios de monitores

## Dónde se suben los horarios

La carga masiva de horarios desde Excel no entra por un endpoint REST; entra por Django Admin.

- Vista de importación: `/admin/schedules/schedule/import-schedules/`
- Implementación admin: `apps/schedules/admin.py`
- Lógica de importación: `apps/schedules/services.py`
- Formulario de carga: `apps/schedules/forms.py`

## Qué valida el sistema

Antes de procesar el archivo, se valida:

- que el archivo tenga extensión Excel (`.xlsx`, etc.) mediante `validate_excel_extension`
- que cada bloque `DIA/HORA` tenga un formato válido
- que la hora final sea mayor que la inicial

Durante la importación:

- se buscan monitores por `codigo_estudiante`
- si el monitor no existe, queda reportado en `missing_monitors`
- si hay bloques consecutivos del mismo día, se fusionan
- si el horario ya existe e estaba inactivo, se reactiva

## Formato esperado del Excel

El archivo debe incluir bloques por monitor con estas etiquetas:

- `NOMBRE`
- `CODIGO`
- `DIA/HORA`

Ejemplos válidos en la columna `DIA/HORA`:

- `LUNES 6-8`
- `MIERCOLES 12-14`
- `VIERNES 14:30-18:00`

## Cómo comprobar que se subieron correctamente

### Opción 1: desde Django Admin

1. Entrar a `/admin/`
2. Ir a `Schedules`
3. Usar `Importar horarios`
4. Confirmar el mensaje final:
   - monitores procesados
   - horarios creados
   - reactivados
   - filas ignoradas
5. Revisar si hubo advertencia de `missing_monitors`

### Opción 2: desde API

Después de importar:

1. Inicia sesión por API en `/api/v1/auth/login/`
2. Consulta monitores en `/api/v1/monitors/`
3. Consulta horarios en `/api/v1/schedules/`
4. Verifica que cada registro tenga:
   - `monitor`
   - `weekday`
   - `start_time`
   - `end_time`
   - `is_active=true`

## Mapeo de `weekday` en API

- `0`: lunes
- `1`: martes
- `2`: miércoles
- `3`: jueves
- `4`: viernes
- `5`: sábado
- `6`: domingo

## Archivos Postman incluidos

- `docs/postman/Monitores - Horarios.postman_collection.json`
- `docs/postman/Monitores - Local.postman_environment.json`

## Flujo recomendado en Postman

### Verificación por API

1. `API Login`
2. `API Me`
3. `List Monitors`
4. `List Schedules`

### Creación manual por API

1. `API Login`
2. `List Monitors`
3. `Create Schedule`
4. `List Schedules`

### Importación masiva por Excel

1. `Admin Login Page`
2. `Admin Login`
3. `Admin Import Form`
4. `Admin Import Schedules Excel`
5. `Admin Schedule List`
6. `List Schedules`

## Notas importantes

- La importación masiva por Excel es una vista de Admin, no una API REST formal.
- Para usar el flujo de Admin en Postman debes usar un usuario con acceso al admin (`is_staff=true`).
- En la colección, la request `Admin Import Schedules Excel` usa `form-data` y requiere seleccionar manualmente el archivo Excel en Postman.
