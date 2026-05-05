# Conciliación vs Horas Extra

## Objetivo

Este documento explica la diferencia entre:

- la **conciliación** de asistencia
- la **revisión de horas extra**

Ambos flujos están conectados, pero no resuelven el mismo problema.

## Resumen corto

- **Conciliación**: responde a la pregunta "¿este registro de asistencia pertenece a qué monitor?"
- **Horas extra**: responde a la pregunta "una vez identificado el monitor y calculada la sesión, ¿ese tiempo extra se aprueba o se rechaza?"

Primero ocurre la conciliación. Después, si el cálculo de la sesión produce tiempo extra, entra el flujo de horas extra.

---

## 1. Qué es la conciliación

La conciliación ocurre cuando el sistema importa un archivo de asistencia y crea registros crudos.

Ese registro crudo todavía no siempre está listo para contar horas válidas, porque el sistema primero debe saber a qué monitor corresponde.

### Archivos principales

- [apps/attendance/services.py](/D:/Monitores/apps/attendance/services.py:83)
- [apps/attendance/models.py](/D:/Monitores/apps/attendance/models.py:38)
- [apps/attendance/views.py](/D:/Monitores/apps/attendance/views.py:28)

### Qué se crea

Se crea un `AttendanceRawRecord`, que guarda:

- nombre crudo
- dependencia cruda
- fecha
- hora de entrada
- hora de salida
- archivo de origen
- posible monitor asociado
- estado de conciliación

### Estados relevantes

En [apps/common/choices.py](/D:/Monitores/apps/common/choices.py:22) el campo `reconciliation_status` usa:

- `pending`
- `matched`
- `manual_review`

### Cómo se concilia automáticamente

La lógica está en [apps/attendance/services.py](/D:/Monitores/apps/attendance/services.py:61), dentro de `_match_monitor` y [apps/attendance/services.py](/D:/Monitores/apps/attendance/services.py:83) en `reconcile_raw_record`.

Hoy el sistema intenta encontrar un monitor con base en:

- `normalized_full_name`

Si encuentra exactamente uno:

- el registro queda `matched`

Si encuentra varios:

- el registro queda en revisión manual

Si no encuentra ninguno:

- el registro queda en revisión manual

### Qué pasa si no se puede conciliar

El registro queda visible en:

- la vista web [templates/attendance/reconciliation_queue.html](/D:/Monitores/templates/attendance/reconciliation_queue.html:1)
- la API de pendientes de conciliación

Y un usuario puede asignar el monitor manualmente desde:

- [apps/attendance/views.py](/D:/Monitores/apps/attendance/views.py:40)
- [apps/attendance/api/views.py](/D:/Monitores/apps/attendance/api/views.py:37)

### Resultado esperado de la conciliación

El resultado correcto de la conciliación no es aprobar horas ni calcular extras. El resultado correcto es solo este:

- el `AttendanceRawRecord` queda asociado a un `Monitor`
- `reconciliation_status = matched`

---

## 2. Qué son las horas extra

Las horas extra aparecen después de la conciliación, no antes.

Una vez que el registro crudo ya está asociado a un monitor, el sistema puede convertirlo en una sesión de trabajo procesada.

### Archivos principales

- [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:20)
- [apps/work_sessions/models.py](/D:/Monitores/apps/work_sessions/models.py:7)
- [apps/work_sessions/views.py](/D:/Monitores/apps/work_sessions/views.py:12)

### Qué se crea

Se crea una `WorkSession`, que representa la sesión ya calculada.

Esta sesión guarda, entre otras cosas:

- hora real de entrada y salida
- hora normalizada de entrada y salida
- horario programado usado
- minutos normales
- minutos extra
- minutos de retardo
- estado de la sesión
- estado de horas extra

### Cuándo aparece tiempo extra

En [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:49) a [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:56) el sistema calcula:

- minutos normales
- minutos tardíos
- total trabajado
- minutos extra

La regla principal es:

```python
overtime = max(total_minutes - normal, 0)
```

Si `overtime > 0`, la sesión queda con:

- `overtime_status = pending`

Si no hay extra:

- `overtime_status = not_applicable`

### Importante

Las horas extra no significan todavía "horas aprobadas".

Primero quedan como **pendientes**. Luego un líder o administrador debe revisarlas.

---

## 3. Flujo completo de punta a punta

El flujo real es este:

1. Se sube un Excel de asistencia.
2. Se crea un `AttendanceImportJob`.
3. Se crean `AttendanceRawRecord`.
4. El sistema intenta conciliar cada registro con un monitor.
5. Si el registro queda `matched` y es procesable, se crea una `WorkSession`.
6. La `WorkSession` calcula normales, retardos y extras.
7. Si hay extra, queda pendiente de revisión.
8. Un líder o admin aprueba o rechaza ese extra.

En una línea:

**Conciliación** identifica el monitor.  
**Work session** calcula la sesión.  
**Horas extra** revisa el excedente calculado.

---

## 4. Diferencia conceptual

### Conciliación

Se enfoca en identidad y trazabilidad.

Pregunta:

- "¿A quién pertenece este registro?"

No decide:

- si el tiempo extra es válido
- si hay penalización
- si se aprueba el excedente

### Horas extra

Se enfoca en validación operativa del tiempo excedente.

Pregunta:

- "¿El tiempo trabajado por fuera del horario debe reconocerse o rechazarse?"

No decide:

- a qué monitor pertenece el registro

---

## 5. Qué pasa cuando la conciliación falla

Si la conciliación falla:

- no se puede generar correctamente la sesión procesada
- el registro queda pendiente
- no entra todavía al flujo real de horas extra

Eso significa que un problema de conciliación bloquea el cálculo posterior.

En términos prácticos:

- sin monitor correcto, no hay sesión confiable
- sin sesión confiable, no hay revisión correcta de horas extra

---

## 6. Qué pasa cuando sí se concilia

Cuando el registro sí queda asociado a un monitor:

- se puede buscar el horario del monitor para ese día
- se puede comparar entrada/salida contra ese horario
- se pueden calcular:
  - normales
  - extras
  - retardos

Ese cálculo ocurre en [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:20).

---

## 7. Qué papel juegan los horarios

Los horarios viven en `schedules`, y sirven como referencia para calcular la sesión.

No son parte de la conciliación.

No son todavía la aprobación de horas extra.

Son la base para decidir:

- cuánto del tiempo trabajado cae dentro del turno
- cuánto queda fuera del turno
- si hubo retardo

Si no existe horario para ese día:

- la sesión puede quedar `without_schedule`
- gran parte o todo el tiempo puede terminar como extra pendiente

Eso está en [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:40).

---

## 8. Qué hace la revisión de horas extra

La revisión de horas extra ocurre en [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:98).

Un líder o admin puede:

- `approve`
- `reject`

### Si aprueba

- `overtime_status = approved`
- `penalty_minutes = 0`

### Si rechaza

- `overtime_status = rejected`
- `penalty_minutes = overtime_minutes`
- se crea una anotación de descuento

O sea:

- la conciliación nunca aprueba extras
- la revisión de extras nunca decide el monitor

---

## 9. Cómo se calculan los retardos

El cálculo de retardos ocurre cuando un `AttendanceRawRecord` ya conciliado se convierte en una `WorkSession`.

Archivos clave:

- [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:20)
- [apps/common/utils.py](/D:/Monitores/apps/common/utils.py:47)
- [apps/common/utils.py](/D:/Monitores/apps/common/utils.py:56)

### Regla general

El sistema no calcula el retardo con la hora exacta de entrada, sino con la **hora normalizada de inicio**.

Primero toma la hora real de entrada y la aproxima con `normalize_session_start`.

Luego compara esa hora normalizada contra la hora inicial del horario programado.

La línea clave está en [apps/work_sessions/services.py](/D:/Monitores/apps/work_sessions/services.py:44):

```python
late = max(duration_in_minutes(normalized_start) - duration_in_minutes(schedule.start_time), 0)
```

Eso significa:

- si la hora normalizada de entrada es mayor que la hora de inicio del turno, hay retardo
- si es igual o menor, el retardo es `0`

### Cómo se normaliza la entrada

La normalización actual de entrada está en [apps/common/utils.py](/D:/Monitores/apps/common/utils.py:47).

La regla es:

- si entra dentro de los primeros 5 minutos de la hora, baja a `:00`
- si entra antes del minuto 45, sube a `:30`
- si entra desde el minuto 45 en adelante, sube a la siguiente hora en `:00`

### Ejemplo

Supongamos un horario programado de:

- `06:00` a `08:00`

Y una entrada real de:

- `06:07`

Entonces:

- `06:07` se normaliza a `06:30`
- el sistema compara `06:30` contra `06:00`
- el resultado es `30` minutos de retardo

### Otro ejemplo

Si la entrada real fuera:

- `06:45`

Entonces:

- `06:45` se normaliza a `07:00`
- el retardo calculado sería `60` minutos

### Qué se guarda

En la `WorkSession` quedan estos campos:

- `late_minutes`
- `is_late`

Si `late_minutes > 0`, entonces:

- `is_late = True`

### Relación con memorando

Los reportes no usan directamente los minutos de retardo para el memorando, sino la cantidad de sesiones marcadas con tardanza.

Eso se refleja en [apps/reports/selectors.py](/D:/Monitores/apps/reports/selectors.py:46), donde se calcula `late_count`.

Si el monitor acumula 3 o más tardanzas dentro del rango evaluado:

- `has_memorandum = True`

### Importante

Actualmente existe una función `late_minutes(...)` en [apps/common/utils.py](/D:/Monitores/apps/common/utils.py:69), pero el flujo principal de `WorkSession` no usa esa función para el cálculo final del retardo.

Hoy el cálculo real del retardo en producción se basa en:

- la entrada normalizada
- la hora programada de inicio

No en una tolerancia separada aplicada a la hora exacta.

---

## 10. Casos típicos

### Caso A: conciliación correcta, sin horas extra

1. Se importa la fila.
2. El sistema encuentra el monitor.
3. Se crea la sesión.
4. Todo el tiempo cae dentro del horario.
5. `overtime_minutes = 0`
6. No hay revisión de horas extra.

### Caso B: conciliación correcta, con horas extra

1. Se importa la fila.
2. El sistema encuentra el monitor.
3. Se crea la sesión.
4. Parte del tiempo queda fuera del horario.
5. `overtime_minutes > 0`
6. La sesión queda pendiente de revisión.

### Caso C: conciliación fallida

1. Se importa la fila.
2. El sistema no encuentra monitor o encuentra varios.
3. El registro queda en conciliación manual.
4. Todavía no hay flujo estable de horas extra hasta resolver esa asociación.

---

## 11. Regla práctica para pensar el sistema

Si quieres entender el sistema rápido, piensa así:

- `attendance` = lo que llegó desde el reloj / Excel
- `conciliation` = a qué monitor pertenece
- `work_session` = cómo queda calculado ese trabajo
- `overtime review` = si el excedente se reconoce o se rechaza

---

## 12. Dónde revisar cada cosa en la interfaz

### Conciliación

- Web: `/imports/reconciliation/`
- API: `/api/v1/attendance/pending-reconciliation/`

### Horas extra

- Web: `/overtime/review/`
- API: `/api/v1/sessions/`
- Acción API: `/api/v1/sessions/{id}/review-overtime/`

---

## 13. Conclusión

La relación entre ambos flujos es secuencial:

1. primero se concilia
2. luego se calcula la sesión
3. después se revisan horas extra, si existen

La conciliación resuelve identidad.  
Las horas extra resuelven decisión sobre el excedente.
