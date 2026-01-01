# Production Deployment Guide - Nginx + Docker + HTTPS

## Overview
This guide walks you through deploying your Django/Daphne application with Nginx reverse proxy and Let's Encrypt SSL on your VPS at `72.60.170.141` with the domain `pineriverapp.com`.

## Architecture
```
┌─────────────────────┐
│  Client (Internet)  │
└──────────┬──────────┘
           │
      (HTTPS:443)
           │
┌──────────▼──────────┐
│  Nginx Reverse Proxy│
│   (Port 80, 443)    │
└──────────┬──────────┘
           │
      (HTTP:8006)
           │
┌──────────▼──────────┐
│ Django (Daphne)     │
│   (Port 8006)       │
└─────────────────────┘
```

## Prerequisites
- VPS with Ubuntu 20.04+ or similar Linux distribution
- Docker and Docker Compose installed
- Domain name `pineriverapp.com` pointing to your server IP `72.60.170.141`
- SSH access to your server
- SSL certificate (obtained via Let's Encrypt)

## Step 1: Prerequisites Setup on Your VPS

### 1.1 Install Docker and Docker Compose
```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 1.2 Install Certbot (locally for initial setup)
```bash
sudo apt-get install certbot python3-certbot-nginx -y
```

## Step 2: Prepare Your Application

### 2.1 Update Your DNS Records
Point your domain to your VPS:
```
pineriverapp.com     A       72.60.170.141
www.pineriverapp.com A       72.60.170.141
```
Wait for DNS propagation (can take up to 24 hours, but usually faster).

### 2.2 Copy Project to VPS
```bash
# On your local machine
git push origin main

# On VPS
cd /home/youruser
git clone https://github.com/yourusername/pdezzy.git
cd pdezzy
```

### 2.3 Create .env File
```bash
cp .env.production .env
nano .env  # Edit with your actual values
```

Edit the .env file with your settings:
```bash
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_HOSTS=pineriverapp.com,www.pineriverapp.com
DB_PASSWORD=your-secure-db-password
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Step 3: Initialize SSL Certificates

### 3.1 First-time Certificate Setup
```bash
# Make the initialization script executable
chmod +x init-letsencrypt.sh

# Run the initialization script
./init-letsencrypt.sh
```

This script will:
1. Create necessary directories
2. Start a temporary Nginx container
3. Use Certbot to obtain SSL certificates from Let's Encrypt
4. Store certificates in `./certbot_data/`

### 3.2 Verify Certificate
```bash
# List certificates
sudo ls -la ./certbot_data/live/pineriverapp.com/
```

You should see:
- `fullchain.pem` - Full certificate chain
- `privkey.pem` - Private key
- `cert.pem` - Certificate
- `chain.pem` - Intermediate certificates

## Step 4: Deploy with Docker Compose

### 4.1 Build and Start Services
```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4.2 Run Migrations
```bash
# The migrations run automatically in the web service startup
# But you can also run manually:
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### 4.3 Verify Services are Running
```bash
# Check if containers are up
docker-compose ps

# Expected output:
# NAME                COMMAND                  SERVICE      STATUS       PORTS
# pdezzy_nginx        "nginx -g daemon off"    nginx        Up 2 minutes  0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443->443/tcp, :::443->443/tcp
# pdezzy_certbot      "/bin/sh -c 'trap..."   certbot      Up 2 minutes
# pdezzy_web          "sh -c 'python..."      web          Up 2 minutes  8006/tcp
# pdezzy_db           "docker-entrypoint..."  db           Up 2 minutes  5433/tcp
# pdezzy_redis        "redis-server"          redis        Up 2 minutes  6380/tcp
```

## Step 5: Test Your Deployment

### 5.1 Test HTTP to HTTPS Redirect
```bash
# Should redirect to HTTPS
curl -I http://pineriverapp.com
# Expected: 301 redirect to https://pineriverapp.com
```

### 5.2 Test HTTPS Connection
```bash
# Should return 200 OK
curl -I https://pineriverapp.com

# Check SSL certificate
openssl s_client -connect pineriverapp.com:443 < /dev/null
```

### 5.3 Test API Endpoint
```bash
curl https://pineriverapp.com/api/
```

### 5.4 Check Logs
```bash
# Nginx logs
docker-compose logs nginx

# Django logs
docker-compose logs web

# Database logs
docker-compose logs db
```

## Step 6: Configure Firewall (UFW)

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

## Step 7: Set Up Auto-Renewal

SSL certificates from Let's Encrypt expire after 90 days. The Certbot container in docker-compose automatically renews them. To verify:

```bash
# Check the renewal date of your certificate
sudo certbot certificates

# Expected output shows renewal date 30 days before expiration
```

## Daily Operations

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f nginx
```

### Update Application
```bash
git pull origin main
docker-compose build
docker-compose up -d
```

### Access Admin Panel
1. Create superuser: `docker-compose exec web python manage.py createsuperuser`
2. Visit: `https://pineriverapp.com/admin/`

### Database Backup
```bash
docker-compose exec db pg_dump -U postgres pdezzy > backup-$(date +%Y%m%d).sql
```

### Database Restore
```bash
docker-compose exec -T db psql -U postgres pdezzy < backup-20240101.sql
```

## Troubleshooting

### Nginx not starting
```bash
# Check Nginx config
docker-compose exec nginx nginx -t

# Check logs
docker-compose logs nginx
```

### SSL certificate issues
```bash
# Check certificate status
docker-compose exec certbot certbot certificates

# Manually renew certificate
docker-compose exec certbot certbot renew --force-renewal
```

### Django errors
```bash
# Check Django logs
docker-compose logs web

# Run Django shell
docker-compose exec web python manage.py shell
```

### Database connection issues
```bash
# Check if database is healthy
docker-compose exec db pg_isready

# Connect to database
docker-compose exec db psql -U postgres -d pdezzy
```

### Permission denied errors
```bash
# Fix volume permissions
docker-compose down
sudo chown -R $USER:$USER .

# Rebuild and restart
docker-compose up -d
```

## Security Best Practices

1. **Change Default Passwords**
   - Database password in `.env`
   - Create Django superuser with strong password

2. **Firewall Configuration**
   - Only allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
   - Block all other inbound traffic

3. **Keep Secrets Secure**
   - Never commit `.env` file to git
   - Use environment variables for sensitive data
   - Rotate API keys regularly

4. **Monitor Logs**
   - Check logs regularly for suspicious activity
   - Set up log rotation for Docker containers

5. **Regular Updates**
   - Keep Docker images updated
   - Update Django dependencies regularly
   - Monitor security advisories

6. **Backup Strategy**
   - Regular database backups
   - Store backups in secure location
   - Test restore procedure periodically

## Performance Optimization

### Enable Caching
The Nginx configuration includes:
- Static file caching (30 days)
- Media file caching (7 days)
- Gzip compression

### Database Optimization
- PostgreSQL connection pooling (CONN_MAX_AGE: 600)
- Use indexes on frequently queried fields
- Regular VACUUM and ANALYZE

### Static Files
- Already handled by Nginx
- Served directly from `/app/staticfiles/`

## Support and Resources

- Django Documentation: https://docs.djangoproject.com/
- Docker Documentation: https://docs.docker.com/
- Nginx Documentation: https://nginx.org/en/docs/
- Let's Encrypt: https://letsencrypt.org/
- Ubuntu Server Guide: https://ubuntu.com/server/docs

---

**Last Updated:** 2024
**Version:** 1.0
