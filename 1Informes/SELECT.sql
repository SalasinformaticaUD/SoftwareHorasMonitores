SELECT 
    u.email,
    m.full_name,
    m.codigo_estudiante,
    CASE m.department
        WHEN 'informatics_labs' THEN 'Monitores Aulas de Software'
        WHEN 'physics' THEN 'Monitores Fisica'
        WHEN 'electrical' THEN 'Monitores Laboratorios'
        ELSE m.department
    END AS department,
    m.numero_documento,
    m.proyecto_curricular,
    m.telefono
FROM monitors_monitor m
LEFT JOIN users_user u ON m.user_id = u.id