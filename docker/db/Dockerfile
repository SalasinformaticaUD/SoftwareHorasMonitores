FROM postgres:16-alpine

COPY initial_users.csv /initial_users.csv
COPY cargarUsuariosIniciales.sql /docker-entrypoint-initdb.d/01-cargarUsuariosIniciales.sql
