COPY users_user (
    password,
    last_login,
    is_superuser,
    username,
    first_name,
    last_name,
    email,
    is_staff,
    is_active,
    date_joined,
    id,
    created_at,
    updated_at,
    role,
    department
) FROM '/app/docker/initial_users.csv' WITH CSV HEADER;