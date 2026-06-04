BEGIN;

CREATE TEMP TABLE deletion_log (
    item text,
    affected_rows integer
);

CREATE TEMP TABLE target_departments AS
SELECT DISTINCT department
FROM users_user
WHERE username = 'leader.labs'
  AND department IS NOT NULL
UNION
SELECT 'informatics_labs';

CREATE TEMP TABLE target_users AS
SELECT id
FROM users_user
WHERE username = 'leader.labs';

CREATE TEMP TABLE target_monitors AS
SELECT id
FROM monitors_monitor
WHERE department IN (SELECT department FROM target_departments);

CREATE TEMP TABLE target_import_jobs_initial AS
SELECT id
FROM attendance_attendanceimportjob
WHERE uploaded_by_id IN (SELECT id FROM target_users);

CREATE TEMP TABLE target_raw_records AS
SELECT DISTINCT r.id
FROM attendance_attendancerawrecord r
WHERE r.monitor_id IN (SELECT id FROM target_monitors)
   OR r.import_job_id IN (SELECT id FROM target_import_jobs_initial)
   OR r.normalized_department IN (
        'monitores',
        'monitores aulas de software',
        'aulas de software',
        'monitorias',
        'monitores aulas de sistemas',
        'salas informatica',
        'informatica',
        'informatics labs',
        'informatics_labs'
   );

CREATE TEMP TABLE target_import_jobs AS
SELECT id FROM target_import_jobs_initial
UNION
SELECT DISTINCT import_job_id
FROM attendance_attendancerawrecord
WHERE id IN (SELECT id FROM target_raw_records);

CREATE TEMP TABLE target_sessions AS
SELECT DISTINCT id
FROM work_sessions_worksession
WHERE monitor_id IN (SELECT id FROM target_monitors)
   OR raw_record_id IN (SELECT id FROM target_raw_records);

CREATE TEMP TABLE target_annotations AS
SELECT DISTINCT id
FROM annotations_annotation
WHERE monitor_id IN (SELECT id FROM target_monitors)
   OR leader_id IN (SELECT id FROM target_users)
   OR session_id IN (SELECT id FROM target_sessions);

CREATE TEMP TABLE target_inconsistencies AS
SELECT DISTINCT id
FROM attendance_attendanceinconsistency
WHERE monitor_id IN (SELECT id FROM target_monitors)
   OR raw_record_id IN (SELECT id FROM target_raw_records)
   OR solution_annotation_id IN (SELECT id FROM target_annotations);

WITH deleted AS (
    DELETE FROM notifications_notification
    WHERE department IN (SELECT department FROM target_departments)
       OR recipient_id IN (SELECT id FROM target_users)
       OR event_type IN (
            'attendance_imported',
            'attendance_reconciliation_failed',
            'session_processed',
            'overtime_pending',
            'overtime_reviewed',
            'annotation_created',
            'report_generated'
       )
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'notifications_notification', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM reports_monitorreportsnapshot
    WHERE monitor_id IN (SELECT id FROM target_monitors)
       OR department IN (SELECT department FROM target_departments)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'reports_monitorreportsnapshot', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM reports_monitormemorandum
    WHERE monitor_id IN (SELECT id FROM target_monitors)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'reports_monitormemorandum', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM attendance_attendanceinconsistencyevent
    WHERE inconsistency_id IN (SELECT id FROM target_inconsistencies)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'attendance_attendanceinconsistencyevent', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM attendance_attendanceinconsistency
    WHERE id IN (SELECT id FROM target_inconsistencies)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'attendance_attendanceinconsistency', COUNT(*) FROM deleted;

WITH updated AS (
    UPDATE attendance_attendanceinconsistency
    SET solution_annotation_id = NULL
    WHERE solution_annotation_id IN (SELECT id FROM target_annotations)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'attendance_inconsistency_solution_annotation_null', COUNT(*) FROM updated;

WITH deleted AS (
    DELETE FROM annotations_annotation
    WHERE id IN (SELECT id FROM target_annotations)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'annotations_annotation', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM work_sessions_worksession
    WHERE id IN (SELECT id FROM target_sessions)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'work_sessions_worksession', COUNT(*) FROM deleted;

WITH updated AS (
    UPDATE attendance_attendancerawrecord
    SET paired_record_id = NULL
    WHERE paired_record_id IN (SELECT id FROM target_raw_records)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'raw_records_paired_record_null', COUNT(*) FROM updated;

WITH updated AS (
    UPDATE attendance_attendancerawrecord
    SET duplicate_of_id = NULL
    WHERE duplicate_of_id IN (SELECT id FROM target_raw_records)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'raw_records_duplicate_of_null', COUNT(*) FROM updated;

WITH deleted AS (
    DELETE FROM attendance_attendancerawrecord
    WHERE id IN (SELECT id FROM target_raw_records)
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'attendance_attendancerawrecord', COUNT(*) FROM deleted;

WITH deleted AS (
    DELETE FROM attendance_attendanceimportjob j
    WHERE j.id IN (SELECT id FROM target_import_jobs)
      AND NOT EXISTS (
          SELECT 1
          FROM attendance_attendancerawrecord r
          WHERE r.import_job_id = j.id
      )
    RETURNING 1
)
INSERT INTO deletion_log SELECT 'attendance_attendanceimportjob', COUNT(*) FROM deleted;

SELECT * FROM deletion_log ORDER BY item;

COMMIT;