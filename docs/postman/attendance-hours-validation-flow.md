# Flujo para validar que el registro de horas está bien

## ¿Es lo mismo que cargar horarios?

No. Son dos flujos distintos:

- **Cargar horarios**: define el turno esperado del monitor.
- **Registrar horas**: importa asistencia real, la concilia con un monitor y genera la sesión trabajada.

En otras palabras:

- `schedules` responde: "¿qué horario debía cumplir?"
- `attendance` + `work_sessions` responden: "¿qué horario registró realmente y cómo quedó calculado?"

## Dónde ocurre cada parte

### Horario esperado

- Modelo: `apps/schedules/models.py`
- API: `/api/v1/schedules/`
- Importación por Excel: Django Admin

### Registro real de horas

- Importación de asistencia: `apps/attendance/services.py`
- API de importación: `/api/v1/attendance/imports/`
- Conciliación manual: `/api/v1/attendance/pending-reconciliation/`
- Sesiones generadas: `/api/v1/sessions/`
- Dashboard resumido: `/api/v1/reports/dashboard/`
- Consulta pública por monitor: `/api/v1/reports/public-monitor-lookup/`

## Flujo real del registro de horas

1. Se sube un Excel de asistencia.
2. Se crea un `AttendanceImportJob`.
3. El sistema procesa filas y crea `AttendanceRawRecord`.
4. Cada fila intenta asociarse automáticamente a un monitor.
5. Si se encuentra el monitor, el registro queda `matched`.
6. Si el registro es procesable, se crea una `WorkSession`.
7. Allí se calculan:
   - `normal_minutes`
   - `overtime_minutes`
   - `late_minutes`
   - `penalty_minutes`
   - `session_state`
   - `overtime_status`

## Qué revisar para saber si quedó bien

### 1. El lote de importación

Endpoint:

- `GET /api/v1/attendance/imports/`

Verifica:

- `status`
- `total_rows`
- `imported_rows`
- `failed_rows`
- `error_message`

Esperado:

- `status = completed`
- `failed_rows = 0` o bajo
- `error_message` vacío

### 2. Los registros pendientes de conciliación

Endpoint:

- `GET /api/v1/attendance/pending-reconciliation/`

Si aparecen registros aquí, significa que el sistema no pudo asociarlos automáticamente al monitor correcto.

Verifica:

- `raw_full_name`
- `raw_department`
- `manual_review_reason`

Si hace falta, se corrige con:

- `POST /api/v1/attendance/pending-reconciliation/{id}/assign-monitor/`

### 3. Las sesiones generadas

Endpoint:

- `GET /api/v1/sessions/`

Aquí es donde realmente puedes comprobar si el cálculo de horas quedó bien.

Campos clave:

- `actual_start`
- `actual_end`
- `normalized_start`
- `normalized_end`
- `scheduled_start`
- `scheduled_end`
- `normal_minutes`
- `overtime_minutes`
- `late_minutes`
- `penalty_minutes`
- `session_state`
- `overtime_status`

## Cómo interpretar una sesión

### Caso correcto esperado

Si existe horario y el monitor fue conciliado:

- debe existir una `WorkSession`
- `session_state` normalmente será `processed`
- `normal_minutes` debe reflejar las horas dentro del turno
- `overtime_minutes` debe reflejar tiempo extra
- `late_minutes` debe reflejar tardanza

### Caso sin horario cargado

Si el monitor no tenía horario para ese día:

- `schedule` no aplica
- `session_state = without_schedule`
- normalmente todo el tiempo puede terminar como extra pendiente

### Caso no conciliado

Si no se pudo asociar el monitor:

- el registro queda en `pending-reconciliation`
- no se crea la sesión hasta que se asigne manualmente

## Encabezados esperados en el Excel de asistencia

El importador espera estos encabezados lógicos:

- `departamento`
- `nro._usuario`
- `id_de_usuario`
- `nombre`
- `fecha_inicio`
- `fecha_fin`
- `descripción_de_la_excepción`
- `tiempo_trabajado`
- `días_de_trabajo`
- `tiempo_de_trabajo`
- `observaciones`

Si faltan, la importación falla.

## Qué endpoints usar en Postman

### Flujo mínimo para validar horas

1. `API Login`
2. `Upload Attendance Excel`
3. `List Import Jobs`
4. `List Pending Reconciliation`
5. `Assign Monitor To Raw Record` si hace falta
6. `List Work Sessions`
7. `Dashboard Summary`
8. `Public Monitor Lookup`

## Cómo decidir si el cálculo es correcto

Para cada monitor o sesión revisa:

- que el horario exista en `/api/v1/schedules/`
- que la asistencia se haya importado sin errores
- que el raw record no haya quedado pendiente de conciliación
- que exista `WorkSession`
- que los minutos normales, extra y retardos tengan sentido frente a:
  - horario programado
  - hora real de entrada
  - hora real de salida
  - reglas de redondeo

## Archivos Postman incluidos

- `docs/postman/Monitores - Registro de Horas.postman_collection.json`
- `docs/postman/Monitores - Local.postman_environment.json`
