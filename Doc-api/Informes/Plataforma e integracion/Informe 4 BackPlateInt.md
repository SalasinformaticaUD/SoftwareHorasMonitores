# Informe 4 - Migración de Backend a API Gestión de Monitores

FECHA: 15/09/2026  
AUTORES: Esteban Bautista

## OBJETIVO DE LA JORNADA

Comparar las ramas `version-2.0` y `Api-gestion-monitores` y trasladar a la rama de integración únicamente los cambios correspondientes a lógica de negocio, modelos, servicios, selectores, migraciones, generación de documentos y endpoints REST.

La migración debía conservar `version-2.0` sin modificaciones y excluir todos los componentes correspondientes al frontend Django, debido a que la interfaz será suministrada por la aplicación general de Software Monitorías.

## CONTROL DE RAMAS

* Todo el trabajo se realizó sobre `Api-gestion-monitores`.
* La rama `version-2.0` se utilizó únicamente como fuente de comparación en modo lectura.
* No se realizaron commits, merges, rebases ni pushes sobre `version-2.0`.
* El último commit comprobado en `version-2.0` fue `4cd5c76` (`.gitignore modificado`).
* Se revisaron los siete commits que existían en `version-2.0` y no estaban presentes inicialmente en `Api-gestion-monitores`.

## CAMBIOS MIGRADOS

### Conciliación y asistencia

* Se ampliaron los nombres reconocidos para las dependencias de Física y Laboratorios durante la conciliación de registros importados.
* Se añadió el reconocimiento de etiquetas como `Monitores Fisica`, `Monitores Laboratorios` y `Laboratorios`.
* Las inconsistencias visibles se limitan al semestre académico activo.
* Los líderes pueden consultar los registros pendientes de conciliación correspondientes a su dependencia.
* La vinculación manual de un registro de asistencia con un monitor quedó restringida exclusivamente a usuarios administradores.
* La restricción también fue llevada al endpoint REST, ya que la implementación original de `version-2.0` dependía de una vista HTML que no existe en la rama API.

Endpoint afectado:

```http
POST /api/v1/attendance/pending-reconciliation/{registroId}/assign-monitor/
Authorization: Bearer <token>
Content-Type: application/json

{
  "monitor_id": "<uuid-monitor>"
}
```

Un líder recibe `403 Forbidden`; un administrador autorizado puede realizar la conciliación.

### Excepciones de horarios

* Las excepciones pueden dirigirse a uno o varios monitores específicos.
* Cada excepción puede limitarse a uno o varios bloques de horario pertenecientes a los monitores seleccionados.
* Se añadió la opción `all_semester` para utilizar automáticamente las fechas del semestre académico activo.
* Se añadió la relación opcional entre la excepción y `AcademicSemester`.
* Se valida que cada bloque seleccionado pertenezca a uno de los monitores incluidos.
* Un líder solamente puede seleccionar monitores pertenecientes a su propia dependencia.
* Las excepciones semestrales requieren que el semestre activo tenga fechas de inicio y finalización configuradas.
* La búsqueda de excepciones para retardos y horas extra considera ahora el monitor y el bloque de horario procesado.
* Crear, modificar o eliminar una excepción no reprocesa retroactivamente las sesiones ya calculadas.
* Se añadió la migración `schedules/0011_scheduleexception_targeting_and_semester.py`.

Ejemplo de creación mediante la API:

```http
POST /api/v1/schedules/exceptions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Permiso de bloque",
  "description": "Excepción autorizada",
  "monitors": ["<uuid-monitor>"],
  "schedules": ["<uuid-horario>"],
  "all_semester": false,
  "start_date": "2026-09-01",
  "end_date": "2026-09-30",
  "department": "physics",
  "ignore_lateness": true,
  "approve_overtime": false,
  "is_active": true
}
```

Cuando `all_semester` es `true`, la API asigna el semestre activo y usa sus fechas configuradas.

### Actas de compromiso

* Se actualizaron los textos, responsabilidades, actividades y causales incluidos en los PDF de actas según la dependencia del monitor.
* Se normalizó la presentación del periodo académico en el encabezado del acta.
* Se añadieron variantes de contenido para Física, Aulas de Software y Laboratorios.
* Se creó `CommitmentActStatusChoices` con los estados `pending`, `accepted` y `rejected`.
* Se creó el modelo `CommitmentActSubmission` para almacenar el archivo firmado, estado de revisión, motivo de rechazo, revisor y fecha de revisión.
* Se añadió la migración `reports/0004_commitmentactsubmission.py`.
* Se mantuvo compatibilidad con actas PDF antiguas almacenadas directamente en `media/actas_compromiso_firmadas`.
* El listado administrativo informa el estado, motivo de rechazo, identificador del envío y fecha de revisión.
* Se habilitó la generación y descarga del acta personalizada por parte del monitor autenticado, conservando los contenidos actualizados de Física, Aulas de Software y Laboratorios presentes en `version-2.0`.

La implementación original dependía de formularios y vistas HTML. En `Api-gestion-monitores` se reemplazó por los siguientes contratos REST:

#### Generar y descargar el acta personalizada

```http
GET /api/v1/reports/commitment-acts/me/pdf/
Authorization: Bearer <token>
```

La API obtiene el monitor asociado al usuario autenticado, selecciona el formato correspondiente a su dependencia e incorpora sus datos, semestre y bloques de horario. Un monitor no puede generar el acta de otro monitor.

#### Consultar el acta del monitor autenticado

```http
GET /api/v1/reports/commitment-acts/me/
Authorization: Bearer <token>
```

#### Cargar un acta firmada

```http
POST /api/v1/reports/commitment-acts/me/
Authorization: Bearer <token>
Content-Type: multipart/form-data

signed_file=<archivo PDF>
```

El archivo debe tener extensión `.pdf` y un tamaño máximo de 10 MB. Cada nuevo envío queda inicialmente en estado `pending`.

#### Aceptar un acta

```http
POST /api/v1/reports/commitment-acts/{monitorId}/review/
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "accept"
}
```

#### Rechazar un acta

```http
POST /api/v1/reports/commitment-acts/{monitorId}/review/
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "reject",
  "rejection_reason": "Falta una firma."
}
```

#### Descargar el acta firmada

```http
GET /api/v1/reports/commitment-acts/{monitorId}/signed-pdf/
Authorization: Bearer <token>
```

Los administradores y líderes solo pueden revisar o descargar actas dentro de su alcance. Un monitor únicamente puede consultar, cargar o descargar su propia acta.

## ELEMENTOS DE FRONTEND EXCLUIDOS

No se migraron los siguientes elementos de `version-2.0`:

* Plantillas ubicadas en `templates/`.
* Formularios Django de reportes y horarios.
* Vistas basadas en `TemplateView`, `FormView` y mensajes web.
* Rutas del portal administrativo renderizado por Django.
* Configuración visual de `django.contrib.admin`.
* Controles, botones y textos específicos de las pantallas antiguas.
* Pruebas cuyo objetivo exclusivo era validar HTML o formularios web.

Las reglas de negocio relevantes de esas vistas fueron adaptadas a endpoints REST para que puedan ser consumidas por el frontend general.

## INTEGRACIÓN CON LA BASE DE DATOS COMPARTIDA

Durante la ejecución local se confirmó que la API de Monitores utiliza la misma instancia PostgreSQL de Gestión de Aulas. En el esquema `public` ya existían las tablas administradas por Prisma, entre ellas `Usuario`, `Rol`, `Permiso`, `Aula`, `PeriodoAcademico` y `_prisma_migrations`.

La variable `DATABASE_URL` compartida contenía el parámetro `?schema=public`. Este formato es reconocido por Prisma, pero `django-environ` lo convertía en una opción de conexión llamada `schema`, que no es válida para `psycopg`. El servidor fallaba con:

```text
psycopg.ProgrammingError: invalid connection option "schema"
```

Se ajustó `config/settings/base.py` para:

1. Extraer el parámetro `schema` recibido desde `DATABASE_URL`.
2. Validar que sea un identificador seguro de PostgreSQL.
3. Traducirlo a la opción válida `-c search_path=public`.
4. Mantener una sola `DATABASE_URL` compatible con Prisma y Django.

Después de comprobar en modo lectura las tablas existentes, se ejecutaron todas las migraciones de Django. Estas agregaron las tablas propias de Monitores y el historial `django_migrations` en el mismo esquema, sin eliminar ni modificar las tablas existentes administradas por Prisma.

## VALIDACIONES REALIZADAS

Se ejecutaron las siguientes comprobaciones sobre `Api-gestion-monitores`:

```powershell
python manage.py check --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
python -m pytest -q
python manage.py migrate --noinput
python manage.py runserver 127.0.0.1:8002 --noreload
```

Resultados:

* Comprobación de Django: aprobada, sin problemas del sistema.
* Comprobación de migraciones: aprobada, sin cambios adicionales por generar.
* Suite automatizada: **69 pruebas aprobadas**.
* Migraciones sobre PostgreSQL compartido: aplicadas correctamente.
* Servidor de desarrollo: iniciado correctamente en `http://127.0.0.1:8002/`.
* `GET /health`: respuesta `200 OK`.
* Verificación de base de datos desde `/health`: `database: ok`.
* `GET /api/schema/`: respuesta `200 OK`.
* `git diff --check`: sin errores de espacios o formato de parche.

Se añadieron pruebas específicas para:

* Creación de excepciones dirigidas a monitores y bloques de horario.
* Consulta de conciliaciones por parte de líderes sin permiso de modificación.
* Carga de actas por parte del monitor autenticado.
* Revisión y rechazo de actas por parte de un administrador.
* Listado de monitores que todavía no tienen un envío de acta.
* Generación del acta personalizada del monitor desde la API.
* Contenido actualizado del acta de Laboratorios para el periodo 2026-III.
* Selección del formato correspondiente a Física, Aulas de Software y Laboratorios.
* Datos académicos y bloques de horario incluidos en el PDF.

## ADVERTENCIAS NO BLOQUEANTES

* Pytest informa que no puede escribir algunos archivos en `.pytest_cache` por permisos de Windows. Esto no afecta la ejecución ni el resultado de las pruebas.
* La generación del esquema OpenAPI muestra advertencias existentes sobre la autenticación JWT personalizada, parámetros UUID y algunas vistas basadas en `APIView` sin serializador declarado para documentación. El esquema responde `200`, pero estas advertencias deben corregirse para obtener una especificación OpenAPI completamente descriptiva.

## PENDIENTES

* Ejecutar en Postman el flujo completo con tokens reales emitidos por Gestión de Aulas.
* Validar carga, aceptación, rechazo y descarga de actas desde el frontend general.
* Validar desde el frontend la selección dependiente de monitores y bloques para las excepciones.
* Completar las anotaciones de OpenAPI para la autenticación JWT y los nuevos endpoints de actas.
* Confirmar la política de respaldo y despliegue de migraciones Django sobre la base compartida antes de producción.
* Versionar el ajuste de compatibilidad de `DATABASE_URL` y este informe en `Api-gestion-monitores` cuando se autorice el commit.

## ESTADO FINAL

La lógica de backend incorporada recientemente en `version-2.0` quedó migrada a `Api-gestion-monitores` sin trasladar el frontend Django. Los flujos que dependían de pantallas fueron convertidos a contratos REST consumibles por el frontend general.

La API puede conectarse a la base PostgreSQL compartida mediante la misma `DATABASE_URL` utilizada por Gestión de Aulas, sus migraciones están aplicadas y el servicio responde correctamente en el puerto `8002`. La rama `version-2.0` permanece sin modificaciones.
