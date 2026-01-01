# Quick Start - Deploy to Production

## 1. SSH into Your VPS
```bash
ssh root@72.60.170.141
# or
ssh user@72.60.170.141
```

## 2. Clone Project
```bash
cd /home/youruser
git clone https://github.com/yourusername/pdezzy.git
cd pdezzy
```

## 3. Configure Environment
```bash
cp .env.production .env
nano .env
# Edit these critical values:
# - SECRET_KEY: Generate a new secure key
# - DB_PASSWORD: Create a strong password
# - DEBUG: Set to False
# - EMAIL credentials
```

## 4. Ensure DNS is Configured
Your domain must point to your IP BEFORE setting up SSL:
```
pineriverapp.com      A  72.60.170.141
www.pineriverapp.com  A  72.60.170.141
```

Test with:
```bash
nslookup pineriverapp.com
# Should show your IP: 72.60.170.141
```

## 5. Initialize SSL Certificates (First Time Only)
```bash
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh
```

## 6. Deploy
```bash
docker-compose build
docker-compose up -d
```

## 7. Verify
```bash
# Check all containers running
docker-compose ps

# Test HTTPS
curl https://pineriverapp.com/api/

# View logs
docker-compose logs -f
```

## 8. Access Admin
```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Visit: https://pineriverapp.com/admin/
```

## That's It!
Your site is now live with:
- ✅ HTTPS enabled
- ✅ Auto-renewing SSL certificates
- ✅ Nginx reverse proxy
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ Full production configuration

## Common Commands

```bash
# View logs
docker-compose logs -f web

# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Backup database
docker-compose exec db pg_dump -U postgres pdezzy > backup.sql

# Execute Django commands
docker-compose exec web python manage.py [command]

# Update application
git pull
docker-compose build
docker-compose up -d
```

---
For detailed information, see PRODUCTION_DEPLOYMENT.md
