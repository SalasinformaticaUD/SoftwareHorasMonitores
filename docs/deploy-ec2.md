# Despliegue en AWS EC2 con Docker Compose

## DecisiÃ³n sobre PostgreSQL

Para este repositorio dejo **PostgreSQL en contenedor dentro del mismo EC2**.

Es la opciÃ³n mÃ¡s razonable aquÃ­ porque:

- cumple el requisito de un solo servidor;
- reduce costo frente a RDS;
- simplifica backup, restauraciÃ³n y operaciÃ³n inicial;
- mantiene la app portable porque todo sigue parametrizado con `DATABASE_URL`.

Si luego necesitas alta disponibilidad, backups gestionados o mantenimiento menos manual, el siguiente paso natural serÃ­a mover la base a RDS y dejar intacto el resto del `compose`.

## 1. Crear la instancia

Sugerencia pragmÃ¡tica:

- Ubuntu 24.04 LTS
- tipo `t3.small` o `t3.medium` si esperas cargas de Celery frecuentes
- disco EBS gp3 de al menos 20 GB

En el security group abre sÃ³lo:

- `22/tcp` desde tu IP
- `8000/tcp` desde tu IP o desde Internet si vas a exponer directo la app

Si luego colocas Nginx o un balanceador delante, expÃ³n `80/443` y no `8000`.

## 2. Instalar Docker y Compose

SegÃºn la documentaciÃ³n oficial de Docker para Ubuntu, instala Docker Engine y el plugin de Compose desde el repositorio oficial:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
newgrp docker
docker compose version
```

## 3. Copiar el proyecto y configurar variables

```bash
git clone <tu-repo> app
cd app
cp .env.example .env
mkdir -p dropzone
```

Edita `.env` y cambia como mÃ­nimo:

- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`

## 4. Levantar los servicios

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

El stack levanta:

- `app`: Django + Gunicorn
- `worker`: Celery worker
- `beat`: Celery beat
- `redis`: broker/cache operativo
- `db`: PostgreSQL persistido en volumen Docker

## 5. Verificar salud

```bash
curl http://YOUR_EC2_IP:8000/healthz/
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 worker
```

## 6. OperaciÃ³n bÃ¡sica

Comandos Ãºtiles:

```bash
docker compose pull
docker compose up -d --build
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py migrate
docker compose logs -f
```

## 7. Backups mÃ­nimos recomendados

- snapshot periÃ³dico del volumen EBS;
- dump lÃ³gico de PostgreSQL con `pg_dump`;
- copia del archivo `.env`.

Ejemplo:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

## Referencias

- [Docker Engine en Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Security groups de EC2](https://docs.aws.amazon.com/console/ec2/security-groups)
