\set ON_ERROR_STOP on
\encoding UTF8
SET client_encoding = 'UTF8';

/*
===============================================================================
CARGAR ANOTACIONES NUEVAS DESDE CSV
===============================================================================

Como usarlo pegando en psql:

1. Copia el CSV al contenedor de base de datos:
   docker compose cp "1Informes/Consultas/anotaciones_monitores.csv" db:/tmp/anotaciones_monitores.csv

2. Entra a psql:
   docker compose exec db psql -U monitores -d monitores

3. Copia y pega todo este archivo en la consola de psql.

El CSV debe tener el mismo encabezado generado por Exportar_anotaciones_monitores.sql.
La carga inserta solo filas nuevas por id y omite las que ya existen.

Reglas importantes:
- Conserva id como UUID unico por anotacion.
- Para sumar horas: action='add' y delta_minutes positivo.
- Para descontar horas: action='deduct' y delta_minutes negativo.
- Para nota informativa: action='note' y delta_minutes=0.
- annotation_type permitido: missing_punch, virtual_hours, permission, novelty.
- session_id puede ir vacio si la anotacion no esta asociada a una sesion.
- La carga directa por SQL no dispara notificaciones de Django.
- Los tableros actuales si cuentan las nuevas anotaciones automaticamente.
- Los snapshots historicos de reports_monitorreportsnapshot no cambian solos.

Si editas el CSV desde Excel, importalo y exportalo como CSV UTF-8.

===============================================================================
*/;

BEGIN;

CREATE TEMP TABLE tmp_annotations_import (
    id text,
    created_at text,
    updated_at text,
    leader_id text,
    leader_username text,
    leader_email text,
    monitor_id text,
    monitor_codigo_estudiante text,
    monitor_nombre text,
    department text,
    department_label text,
    session_id text,
    session_work_day text,
    annotation_type text,
    annotation_type_label text,
    action text,
    action_label text,
    delta_minutes text,
    delta_hours text,
    occurred_on text,
    description text
) ON COMMIT DROP;

COPY tmp_annotations_import (
    id,
    created_at,
    updated_at,
    leader_id,
    leader_username,
    leader_email,
    monitor_id,
    monitor_codigo_estudiante,
    monitor_nombre,
    department,
    department_label,
    session_id,
    session_work_day,
    annotation_type,
    annotation_type_label,
    action,
    action_label,
    delta_minutes,
    delta_hours,
    occurred_on,
    description
) FROM '/tmp/anotaciones_monitores.csv'
WITH (
    FORMAT csv,
    HEADER true,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"'
);

DO $$
DECLARE
    invalid_count integer;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import
    WHERE id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR leader_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR monitor_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR (
            NULLIF(BTRIM(session_id), '') IS NOT NULL
            AND session_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       );
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) con UUID invalido en id, leader_id, monitor_id o session_id.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import
    WHERE annotation_type NOT IN ('missing_punch', 'virtual_hours', 'permission', 'novelty')
       OR action NOT IN ('add', 'deduct', 'note')
       OR delta_minutes !~ '^-?[0-9]+$';
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) con tipo, accion o delta_minutes invalido.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import
    WHERE (action = 'add' AND delta_minutes::integer < 0)
       OR (action = 'deduct' AND delta_minutes::integer > 0)
       OR (action = 'note' AND delta_minutes::integer <> 0)
       OR ABS(delta_minutes::integer) > 1440;
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) que no cumplen las reglas de horas por accion.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import t
    LEFT JOIN users_user u ON u.id = t.leader_id::uuid
    WHERE u.id IS NULL;
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) con leader_id inexistente.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import t
    LEFT JOIN monitors_monitor m ON m.id = t.monitor_id::uuid
    WHERE m.id IS NULL;
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) con monitor_id inexistente.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import t
    INNER JOIN monitors_monitor m ON m.id = t.monitor_id::uuid
    WHERE t.department <> m.department;
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) donde department no coincide con la dependencia del monitor.', invalid_count;
    END IF;

    SELECT COUNT(*) INTO invalid_count
    FROM tmp_annotations_import t
    LEFT JOIN work_sessions_worksession ws ON ws.id = NULLIF(BTRIM(t.session_id), '')::uuid
    WHERE NULLIF(BTRIM(t.session_id), '') IS NOT NULL
      AND ws.id IS NULL;
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Hay % fila(s) con session_id inexistente.', invalid_count;
    END IF;
END $$;

SELECT
    COUNT(*) AS filas_en_csv,
    COUNT(*) FILTER (
        WHERE EXISTS (
            SELECT 1
            FROM annotations_annotation a
            WHERE a.id = tmp_annotations_import.id::uuid
        )
    ) AS filas_ya_existentes,
    COUNT(*) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM annotations_annotation a
            WHERE a.id = tmp_annotations_import.id::uuid
        )
    ) AS filas_nuevas_por_insertar
FROM tmp_annotations_import;

INSERT INTO annotations_annotation (
    id,
    created_at,
    updated_at,
    department,
    annotation_type,
    description,
    action,
    delta_minutes,
    occurred_on,
    leader_id,
    monitor_id,
    session_id
)
SELECT
    t.id::uuid,
    COALESCE(NULLIF(BTRIM(t.created_at), '')::timestamptz, NOW()),
    COALESCE(NULLIF(BTRIM(t.updated_at), '')::timestamptz, NOW()),
    t.department,
    t.annotation_type,
    t.description,
    t.action,
    t.delta_minutes::integer,
    t.occurred_on::date,
    t.leader_id::uuid,
    t.monitor_id::uuid,
    NULLIF(BTRIM(t.session_id), '')::uuid
FROM tmp_annotations_import t
ON CONFLICT (id) DO NOTHING;

COMMIT;

SELECT 'Carga terminada. Las anotaciones nuevas ya cuentan en las metricas actuales del sistema.' AS resultado;
