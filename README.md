# Monitores

Backend-first para gestion de horas de monitores universitarios con Django, Django REST Framework y PostgreSQL.

## Funcionalidad actual

- Autenticacion web y API con roles `admin` y `leader`.
- Gestion de monitores desde API y Django admin.
- Gestion de horarios semanales por monitor.
- Importacion manual de asistencia desde Excel.
- Importacion automatica semanal desde un archivo en `dropzone`.
- Conciliacion automatica y manual de registros de asistencia.
- Procesamiento de sesiones de trabajo, horas normales, horas extra y tardanzas.
- Revision de horas extra con aprobacion, rechazo y penalizacion.
- Registro de anotaciones con suma o descuento de minutos.
- Dashboard para lideres y administradores.
- Consulta publica limitada por codigo de estudiante y dependencia.
- Generacion de snapshots de reportes por rango de fechas.
- Notificaciones internas basadas en eventos del dominio.
- Documentacion OpenAPI con `drf-spectacular`.

## Modulos principales

- `users`: autenticacion, roles y segregacion por dependencia.
- `monitors`: catalogo de monitores.
- `schedules`: horarios semanales.
- `attendance`: importacion, registros crudos y conciliacion.
- `work_sessions`: procesamiento de sesiones y revision de horas extra.
- `annotations`: ajustes manuales auditables.
- `reports`: dashboard, snapshots y consulta publica.
- `notifications`: alertas internas.

La arquitectura resumida esta en `docs/architecture.md`.

## Rutas web

- `GET /login/`
- `POST /logout/`
- `GET /dashboard/`
- `GET|POST /imports/upload/`
- `GET|POST /imports/reconciliation/`
- `GET|POST /overtime/review/`
- `GET|POST /consulta/`
- `GET /admin/`

## API principal

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`
- `GET|POST /api/v1/monitors/`
- `GET|POST /api/v1/schedules/`
- `GET|POST /api/v1/attendance/imports/`
- `GET /api/v1/attendance/pending-reconciliation/`
- `POST /api/v1/attendance/pending-reconciliation/{id}/assign-monitor/`
- `GET /api/v1/sessions/`
- `POST /api/v1/sessions/{id}/review-overtime/`
- `GET|POST /api/v1/annotations/`
- `GET /api/v1/reports/dashboard/`
- `POST /api/v1/reports/generate/`
- `GET /api/v1/reports/snapshots/`
- `GET /api/v1/reports/public-monitor-lookup/?codigo_estudiante=...&department=...`
- `GET /api/v1/notifications/`
- `POST /api/v1/notifications/{id}/mark-read/`
- `GET /api/schema/`
- `GET /api/docs/`

## Integración con Gestión de Aulas

La integración mantiene bases de datos separadas y usa HTTP. Para el cliente de
Gestión de Aulas están disponibles estas rutas sin prefijo:

- `GET /health`: estado de la API.
- `GET /usuarios/{usuarioExternoId}`: vínculo puntual de un usuario central con
  un monitor. Devuelve `{ id, usuarioExternoId, nombre, estado }` o `404` cuando
  el usuario no tiene monitor asociado.

`usuarioExternoId` es el UUID de Gestión de Aulas guardado de forma opcional y
única en cada monitor. Las rutas funcionales existentes de Monitores no cambian.

## Arranque rapido con Docker

1. Ajusta las variables de entorno en `.env`.
2. Levanta la aplicacion con `docker compose up --build`.
3. Ejecuta migraciones con `docker compose exec web python manage.py migrate`.
4. Carga datos semilla con `docker compose exec web python manage.py seed_initial_data`.
5. Abre `http://localhost:8000`.

## Desarrollo local sin Docker

1. Crea y activa un entorno virtual con Python 3.12 o superior.
2. Instala dependencias con `pip install -r requirements.txt`.
3. Configura PostgreSQL.
4. Ejecuta:
   - `python manage.py migrate`
   - `python manage.py seed_initial_data`
   - `python manage.py runserver`

`config.settings.local` ejecuta las tareas de importación de forma síncrona en local.

## Variables de entorno utiles

- `DATABASE_URL`
- `TIME_ZONE`
- `IMPORT_DROPZONE_PATH`
- `SEED_DEFAULT_PASSWORD`

## Usuarios semilla

- Administrador: `admin` / `ChangeMe123!`
- Lider Fisica: `leader.physics` / `ChangeMe123!`
- Lider Informatica: `leader.labs` / `ChangeMe123!`
- Lider Electrica: `leader.electrical` / `ChangeMe123!`

## Datos semilla

El comando `python manage.py seed_initial_data` crea:

- usuarios base para pruebas locales;
- monitores iniciales por dependencia;
- horarios minimos para esos monitores.

## Pruebas

Ejecuta `pytest tests`.

Si estas en Windows y aparece un problema con carpetas temporales o cache de `pytest`, limpia las carpetas temporales del workspace y vuelve a correr la suite con un `--basetemp` dentro de un directorio que tengas controlado.


## BLOQUEO DE DIRECCIONES
Powershell Admin

New-NetFirewallRule -DisplayName "Block Django 8000 10.20.160" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Block `
  -RemoteAddress Any

Añadir en RemoteAddress las direcciones o subredes que se quieran bloquear

New-NetFirewallRule -DisplayName "Allow Django 8000 10.20.150" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow `
  -RemoteAddress 10.20.150.0/24 

Añadir en RemoteAddress las direcciones o subredes que se quieran permitir

Agregar en .env en ALLOWED_HOSTS la direccion 10.20.150.11
