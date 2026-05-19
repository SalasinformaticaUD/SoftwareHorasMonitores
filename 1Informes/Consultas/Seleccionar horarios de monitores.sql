SELECT 
    u.email AS email_monitor,
    CASE s.weekday
        WHEN 0 THEN 'Lunes'
        WHEN 1 THEN 'Martes'
        WHEN 2 THEN 'Miércoles'
        WHEN 3 THEN 'Jueves'
        WHEN 4 THEN 'Viernes'
        WHEN 5 THEN 'Sábado'
        WHEN 6 THEN 'Domingo'
    END AS day,
    s.start_time,
    s.end_time,
    s.location,
    s.asignatura,
    s.grupo,
    s.docente,
    s.proyecto_curricular
FROM schedules_schedule s
INNER JOIN monitors_monitor m ON s.monitor_id = m.id
INNER JOIN users_user u ON m.user_id = u.id
WHERE s.is_active = true