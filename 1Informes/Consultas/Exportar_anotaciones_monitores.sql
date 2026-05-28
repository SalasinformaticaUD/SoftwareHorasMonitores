\set ON_ERROR_STOP on
\encoding UTF8
SET client_encoding = 'UTF8';

/*
===============================================================================
EXPORTAR ANOTACIONES DE TODOS LOS MONITORES A CSV
===============================================================================

Como usarlo pegando en psql:

1. Entra a psql:
   docker compose exec db psql -U monitores -d monitores

2. Copia y pega todo este archivo en la consola de psql.

3. El CSV queda dentro del contenedor en:
   /tmp/anotaciones_monitores.csv

4. Para traerlo a Windows:
   docker compose cp db:/tmp/anotaciones_monitores.csv "C:\Users\Administrador.WIN-V7MGTG2TNMP\Downloads"

El CSV se genera en UTF-8 para conservar tildes y caracteres como ñ.
Para abrirlo en Excel, usa Datos > Desde texto/CSV y selecciona UTF-8.

Nota sobre las horas:
Las anotaciones se cuentan automaticamente en los tableros actuales porque el
sistema suma annotations_annotation.delta_minutes cada vez que calcula las
metricas del monitor.
===============================================================================
*/;

COPY (
    SELECT
        a.id,
        a.created_at,
        a.updated_at,
        a.leader_id,
        l.username AS leader_username,
        l.email AS leader_email,
        a.monitor_id,
        m.codigo_estudiante AS monitor_codigo_estudiante,
        m.full_name AS monitor_nombre,
        a.department,
        CASE a.department
            WHEN 'informatics_labs' THEN 'Monitores Aulas de Software'
            WHEN 'physics' THEN 'Monitores Fisica'
            WHEN 'electrical' THEN 'Monitores Laboratorios'
            ELSE a.department
        END AS department_label,
        a.session_id,
        ws.work_day AS session_work_day,
        a.annotation_type,
        CASE a.annotation_type
            WHEN 'missing_punch' THEN 'Olvido de registro'
            WHEN 'virtual_hours' THEN 'Horas virtuales'
            WHEN 'permission' THEN 'Permiso'
            WHEN 'novelty' THEN 'Novedad'
            ELSE a.annotation_type
        END AS annotation_type_label,
        a.action,
        CASE a.action
            WHEN 'add' THEN 'Agregar'
            WHEN 'deduct' THEN 'Descontar'
            WHEN 'note' THEN 'Solo anotar'
            ELSE a.action
        END AS action_label,
        a.delta_minutes,
        ROUND(a.delta_minutes::numeric / 60, 2) AS delta_hours,
        a.occurred_on,
        a.description
    FROM annotations_annotation a
    INNER JOIN monitors_monitor m ON m.id = a.monitor_id
    INNER JOIN users_user l ON l.id = a.leader_id
    LEFT JOIN work_sessions_worksession ws ON ws.id = a.session_id
    ORDER BY a.occurred_on, m.full_name, a.created_at
) TO '/tmp/anotaciones_monitores.csv'
WITH (
    FORMAT csv,
    HEADER true,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    FORCE_QUOTE *
);

SELECT 'CSV exportado en /tmp/anotaciones_monitores.csv con codificacion UTF-8.' AS resultado;
