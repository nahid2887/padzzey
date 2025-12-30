# Docker Setup Guide

## Prerequisites
- Docker installed (https://docs.docker.com/get-docker/)
- Docker Compose installed (comes with Docker Desktop)

## Quick Start

### 1. Create Environment File
```bash
cp .env.example .env
```

Edit `.env` with your settings (optional for development):
```
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,10.10.13.27
DB_PASSWORD=your_secure_password
```

### 2. Build and Run
```bash
# Build the Docker images
docker-compose build

# Start all services (web, database, redis)
docker-compose up -d

# View logs
docker-compose logs -f web
```

### 3. Access the Application
- **API Server**: http://10.10.13.27:8006/
- **Swagger Documentation**: http://10.10.13.27:8006/api/docs/
- **Database**: PostgreSQL on localhost:5432

### 4. Common Commands

#### Run migrations
```bash
docker-compose exec web python manage.py migrate
```

#### Create superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

#### Collect static files
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

#### Access shell
```bash
docker-compose exec web python manage.py shell
```

#### View logs
```bash
docker-compose logs -f web        # Django logs
docker-compose logs -f db         # Database logs
docker-compose logs -f redis      # Redis logs
```

#### Stop services
```bash
docker-compose down
```

#### Stop and remove volumes (clean slate)
```bash
docker-compose down -v
```

## WebSocket Configuration

Your application uses Django Channels with Daphne. The configuration:
- **Server**: Daphne ASGI server running on port 8006
- **Redis**: Message broker for WebSocket support
- **Channel Layer**: Redis backend for multi-worker support

WebSocket endpoint: `ws://10.10.13.27:8006/ws/`

## Production Notes

For production deployment:
1. Set `DEBUG=False` in `.env`
2. Use a proper `SECRET_KEY` (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
3. Add proper `ALLOWED_HOSTS`
4. Use environment-specific database passwords
5. Consider using Nginx as reverse proxy
6. Enable HTTPS/SSL certificates

## Docker Network

All services communicate via the `pdezzy_network`:
- `web` service accessible at port 8006
- `db` service accessible to web at `db:5432`
- `redis` service accessible to web at `redis:6379`

## Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
lsof -i :8006

# Use a different port in docker-compose.yml
# Change: "8006:8006" to "8007:8006"
```

### Database Connection Error
```bash
# Check database is running
docker-compose ps

# View database logs
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up -d
```

### Static Files Not Loading
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Clear Docker Cache
```bash
docker system prune -a
docker-compose build --no-cache
```
