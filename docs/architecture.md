# Supuestos y decisiones

- Se implementa un monolito modular con fronteras por dominio: `users`, `monitors`, `schedules`, `attendance`, `work_sessions`, `annotations`, `reports` y `notifications`.
- `openpyxl` se usa para importación Excel en modo `read_only`, porque el formato esperado es tabular y esta opción evita sorpresas de tipado y consumo de memoria de `pandas`.
- La conciliación inicial usa coincidencia exacta normalizada por nombre completo y departamento. Si hay cero o múltiples coincidencias, el registro queda en validación manual.
- Cuando un monitor no tiene horario para un día concreto, la sesión igual se genera, queda marcada como `without_schedule` y el tiempo trabajado se clasifica como extra pendiente.
- El indicador de memorando se considera activo cuando el monitor acumula 3 o más retardos dentro del rango consultado. Es una decisión razonable porque los PDFs sólo mencionan acumulación de retardos, no un umbral exacto.
- La consulta pública no expone listados y exige código de estudiante más departamento, con rate limiting anónimo.
- `ReporteMonitor` se implementa como snapshot persistido regenerable. Esto permite auditoría, respuesta rápida y una futura extracción del módulo de reportes sin depender de consultas transaccionales pesadas.

# Arquitectura

## Estilo

Arquitectura backend-first con Django + DRF sobre un monolito modular. Cada app contiene modelos, servicios, selectores, API y tareas cuando aplica.

## Fronteras de dominio

- `users`: autenticación, roles y segregación por dependencia.
- `monitors`: catálogo de monitores.
- `schedules`: turnos semanales configurables.
- `attendance`: importación de Croschex, almacenamiento crudo y conciliación.
- `work_sessions`: procesamiento de sesiones, cálculo de horas y revisión de extras.
- `annotations`: ajustes manuales trazables.
- `reports`: snapshots y agregados de consulta.
- `notifications`: alertas internas basadas en eventos.

## Patrones pragmáticos

- `services`: orquestación de casos de uso.
- `selectors`: lecturas complejas y dashboards.
- `api`: serializers y vistas DRF delgadas.
- `tasks`: trabajo asíncrono con Celery.
- `events`: publicación de eventos internos desacoplados.

## Evolución futura a microservicios

Los mejores candidatos de extracción son:

1. `attendance`: ya tiene contrato claro alrededor de import jobs y raw records.
2. `work_sessions`: encapsula reglas críticas de cálculo y revisión.
3. `reports`: opera bien como pipeline regenerable y puede moverse a procesamiento offline.
4. `notifications`: consume eventos y puede sustituirse por correo, cola o push sin tocar el core.

La estrategia de extracción sería:

1. Cambiar el `event_bus` interno por un publisher real.
2. Convertir servicios de aplicación en adaptadores de mensajes o HTTP.
3. Mantener los modelos internos del monolito como anti-corruption layer mientras el módulo extraído madura.

# Árbol de carpetas

```text
project/
├── config/
├── apps/
│   ├── common/
│   ├── users/
│   ├── monitors/
│   ├── schedules/
│   ├── attendance/
│   ├── work_sessions/
│   ├── annotations/
│   ├── reports/
│   └── notifications/
├── templates/
├── tests/
├── docker/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

# Modelo de datos

- `users.User`: usuario autenticable con rol y dependencia.
- `monitors.Monitor`: monitor con UUID interno y `codigo_estudiante` único.
- `schedules.Schedule`: horario semanal por monitor y día.
- `attendance.AttendanceImportJob`: lote de importación, estado y archivo fuente.
- `attendance.AttendanceRawRecord`: registro crudo inmutable con conciliación y trazabilidad.
- `work_sessions.WorkSession`: sesión derivada 1 a 1 desde registro crudo.
- `annotations.Annotation`: ajuste auditable con delta de minutos firmado.
- `reports.MonitorReportSnapshot`: snapshot agregado por rango.
- `notifications.Notification`: alerta interna por evento.

