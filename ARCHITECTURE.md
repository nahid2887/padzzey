# Deployment Architecture & Configuration Guide

## 🏗️ Complete System Architecture

```
╔════════════════════════════════════════════════════════════════════════════╗
║                          PRODUCTION ENVIRONMENT                             ║
║                     pineriverapp.com → 72.60.170.141                        ║
╚════════════════════════════════════════════════════════════════════════════╝

                              INTERNET USERS
                                   │
                    HTTP (80)       │      HTTPS (443)
                    ┌──────────────┼──────────────┐
                    │                             │
              ┌─────▼─────────────────────────────▼──────┐
              │                                           │
              │         NGINX REVERSE PROXY               │
              │         (pdezzy_nginx)                    │
              │                                           │
              │  Features:                                │
              │  • SSL/TLS Termination (443)              │
              │  • HTTP→HTTPS Redirect (80)               │
              │  • Gzip Compression                       │
              │  • Security Headers                       │
              │  • Static File Serving                    │
              │  • WebSocket Support                      │
              │  • Load Balancing                         │
              │                                           │
              └─────────────┬──────────────────────────────┘
                            │
                 Internal HTTP (8006)
                            │
              ┌─────────────▼──────────────┐
              │                             │
              │   DJANGO/DAPHNE ASGI       │
              │   (pdezzy_web:8006)         │
              │                             │
              │   Features:                 │
              │   • REST API                │
              │   • WebSocket Support       │
              │   • Admin Panel             │
              │   • Static Files (via nginx)│
              │   • Media Files (via nginx) │
              │                             │
              └──────┬──────────┬──────┬────┘
                     │          │      │
        ┌────────────┼──────────┼──────┼──────────────┐
        │            │          │      │              │
        ▼            ▼          ▼      ▼              ▼
    ┌────────┐  ┌────────┐  ┌──────┐┌──────┐   ┌──────────┐
    │   DB   │  │ Redis  │  │Media ││Static│   │ Let's    │
    │        │  │        │  │Files ││Files │   │ Encrypt  │
    │ PG:5433│  │:6380   │  │      ││      │   │ Certs    │
    │        │  │        │  │      ││      │   │          │
    └────────┘  └────────┘  └──────┘└──────┘   └──────────┘
```

## 📦 Docker Services Composition

```
┌─────────────────────────────────────────────────────────────────────┐
│                    docker-compose.yml (5 Services)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SERVICE 1: NGINX (Reverse Proxy)                                  │
│  ├─ Image: nginx:alpine                                            │
│  ├─ Ports: 80:80, 443:443                                          │
│  ├─ Volumes: nginx.conf, SSL certs, static files, media            │
│  └─ Network: pdezzy_network                                        │
│                                                                     │
│  SERVICE 2: WEB (Django/Daphne)                                    │
│  ├─ Build: ./Dockerfile                                            │
│  ├─ Port: 8006 (internal only)                                     │
│  ├─ Volumes: source code, static files, media                      │
│  ├─ Depends On: db, redis (health checks)                          │
│  └─ Network: pdezzy_network                                        │
│                                                                     │
│  SERVICE 3: DATABASE (PostgreSQL)                                  │
│  ├─ Image: postgres:15                                             │
│  ├─ Port: 5433:5432 (for local access only)                        │
│  ├─ Volume: postgres_data                                          │
│  ├─ Health Check: pg_isready every 10s                             │
│  └─ Network: pdezzy_network                                        │
│                                                                     │
│  SERVICE 4: REDIS (Cache/Message Broker)                           │
│  ├─ Image: redis:7-alpine                                          │
│  ├─ Port: 6380:6379 (for local access only)                        │
│  ├─ Health Check: redis-cli ping every 10s                         │
│  └─ Network: pdezzy_network                                        │
│                                                                     │
│  SERVICE 5: CERTBOT (SSL Auto-Renewal)                             │
│  ├─ Image: certbot/certbot:latest                                  │
│  ├─ Volumes: SSL certificates, webroot                             │
│  ├─ Runs: Daily renewal check                                      │
│  └─ Network: pdezzy_network                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔐 SSL/HTTPS Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSL/TLS Certificate Flow                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INITIAL SETUP (First Time Only)                              │
│  ═════════════════════════════════                            │
│                                                                 │
│  1. Run: ./init-letsencrypt.sh                                 │
│      ↓                                                          │
│  2. Certbot requests certificate from Let's Encrypt            │
│      ↓                                                          │
│  3. Let's Encrypt validates domain ownership via HTTP          │
│      ↓                                                          │
│  4. Certificate issued and stored in ./certbot_data/           │
│      ↓                                                          │
│  5. Nginx loads certificate on startup                         │
│      ↓                                                          │
│  ✓ HTTPS ready!                                                │
│                                                                 │
│  AUTOMATIC RENEWAL (Daily Check)                              │
│  ═════════════════════════════════════════                    │
│                                                                 │
│  Certbot container runs daily:                                 │
│  ├─ Checks certificate expiration                             │
│  ├─ If < 30 days until expiry: renews automatically           │
│  ├─ Validates with Let's Encrypt again                        │
│  ├─ Updates certificate files                                 │
│  ├─ Nginx automatically reloads (no downtime)                 │
│  └─ Process repeats daily                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📂 Project File Structure

```
pdezzy/                              (Root Project Directory)
├── nginx/                           (Nginx Configuration)
│   ├── Dockerfile                  (Nginx container definition)
│   └── nginx.conf                  (Nginx configuration)
│
├── pdezzy/                          (Django Project)
│   ├── pdezzy/                     (Main Django App)
│   │   ├── settings.py             (Updated for production)
│   │   ├── asgi.py                (Daphne ASGI config)
│   │   ├── wsgi.py                (WSGI config)
│   │   └── urls.py
│   │
│   ├── agent/                      (Agent App)
│   ├── buyer/                      (Buyer App)
│   ├── seller/                     (Seller App)
│   ├── messaging/                  (Messaging App)
│   ├── common/                     (Common App)
│   ├── superadmin/                 (Admin App)
│   │
│   ├── manage.py                   (Django CLI)
│   ├── static/                     (Collected static files)
│   ├── media/                      (User uploads)
│   └── db.sqlite3                  (Dev database - replaced by PostgreSQL in prod)
│
├── frontend/                        (React/Frontend - if applicable)
│   ├── components/
│   └── examples/
│
├── docker-compose.yml              (Main Docker orchestration)
├── Dockerfile                      (Django/Daphne container)
│
├── .env.production                 (Environment template)
├── .env                            (Actual environment - DO NOT COMMIT)
│
├── init-letsencrypt.sh             (SSL initialization script)
├── health-check.sh                 (Service health monitoring)
├── pre-deploy-check.sh             (Pre-deployment checklist)
│
├── PRODUCTION_DEPLOYMENT.md        (Complete guide)
├── QUICKSTART.md                  (Quick deployment)
├── SETUP_COMPLETE.md              (Setup summary)
├── DEPLOYMENT_READY.md            (Deployment overview)
├── DEPLOYMENT_CHECKLIST.md        (Pre-flight checklist)
│
└── requirements.txt                (Python dependencies)
```

## 🔄 Request Flow

```
CLIENT REQUEST FLOW:
═══════════════════

1. Client visits https://pineriverapp.com/api/users/
   │
   ├─ SSL Handshake
   │  └─ Certificate verified (Let's Encrypt)
   │
   ├─ HTTP/2 over TLS established
   │
2. Request reaches Nginx (443)
   │
   ├─ Nginx logs request (access logs)
   ├─ Applies gzip compression
   ├─ Adds security headers
   ├─ Routes to Django backend
   │
3. Request reaches Django (8006 internal)
   │
   ├─ CORS check passes
   ├─ CSRF token verified
   ├─ JWT authentication
   ├─ Route to correct view
   │
4. Django processes request
   │
   ├─ Authenticates user
   ├─ Queries PostgreSQL database
   ├─ Processes business logic
   ├─ Returns JSON response
   │
5. Response travels back through Nginx
   │
   ├─ Compresses with gzip
   ├─ Adds cache headers
   ├─ Encrypts with TLS
   │
6. Client receives HTTPS response
   │
   └─ ✓ Request complete
```

## ⚙️ Environment Variables

```
.env Configuration:
═══════════════════

# Django Security
DEBUG=False                          # MUST be False in production
SECRET_KEY=<unique-secure-key>       # Change from default
ALLOWED_HOSTS=pineriverapp.com,www.pineriverapp.com

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=pdezzy
DB_USER=postgres
DB_PASSWORD=<strong-password>        # Change this!
DB_HOST=db
DB_PORT=5432

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<app-password>

# API Keys
LONE_WOLF_API_KEY=<your-api-key>

# OTP Settings
OTP_EXPIRY_MINUTES=10
OTP_LENGTH=6

# Redis
REDIS_URL=redis://redis:6379/0
```

## 🛡️ Security Layers

```
SECURITY ARCHITECTURE:
══════════════════════

Layer 1: SSL/TLS (Nginx)
├─ TLS 1.2 & 1.3 only
├─ Strong cipher suites
├─ Certificate pinning ready
└─ Perfect Forward Secrecy

Layer 2: HTTP Security Headers
├─ HSTS (max-age=31536000)
├─ X-Frame-Options: SAMEORIGIN
├─ X-Content-Type-Options: nosniff
├─ X-XSS-Protection: 1; mode=block
└─ Referrer-Policy: no-referrer-when-downgrade

Layer 3: Application Security (Django)
├─ CSRF token verification
├─ CORS policy enforcement
├─ JWT authentication
├─ Password hashing (bcrypt/argon2)
└─ SQL injection protection (ORM)

Layer 4: Network Security
├─ Firewall rules (UFW)
│  ├─ Port 22 (SSH) - restricted IP
│  ├─ Port 80 (HTTP) - public
│  └─ Port 443 (HTTPS) - public
├─ No direct database access
└─ No internal service exposure

Layer 5: Data Security
├─ PostgreSQL with strong password
├─ Encrypted database connections
├─ Regular backups
└─ GDPR compliance ready
```

## 📊 Performance Optimization

```
PERFORMANCE FEATURES:
════════════════════

Caching:
├─ Static files: 30-day browser cache
├─ Media files: 7-day browser cache
├─ Redis: In-memory cache for Django
└─ PostgreSQL: Connection pooling (600s max age)

Compression:
├─ Gzip: Enabled for text content
├─ Minified CSS/JS: Via Django staticfiles
└─ Image optimization: Via Pillow

Load Balancing:
├─ Nginx: Distributes to Django
├─ PostgreSQL: Connection pooling
└─ Redis: Handles session storage

Monitoring:
├─ Healthchecks: Every 10s for db/redis
├─ Service logs: Aggregated in docker-compose
├─ Custom health-check.sh script
└─ SSL expiry monitoring (certbot)
```

## 🔐 Certificate Details

```
Let's Encrypt Certificate Information:
═══════════════════════════════════════

Certificate Type:    X.509 v3
Issuer:              Let's Encrypt Authority X3
Subject:             pineriverapp.com
Subject Alt Names:   www.pineriverapp.com
Validity:            90 days
Key Size:            2048-bit RSA
Signature Algorithm: sha256WithRSAEncryption

Storage Location:
├─ Full chain:       /etc/letsencrypt/live/pineriverapp.com/fullchain.pem
├─ Private key:      /etc/letsencrypt/live/pineriverapp.com/privkey.pem
├─ Certificate:      /etc/letsencrypt/live/pineriverapp.com/cert.pem
└─ Chain:            /etc/letsencrypt/live/pineriverapp.com/chain.pem

Renewal Schedule:
├─ Check: Daily by certbot container
├─ Trigger: < 30 days until expiry
├─ Process: Automatic, no downtime
└─ Notification: Email (from Let's Encrypt)
```

## 🚀 Deployment Sequence

```
DEPLOYMENT STEPS:
═════════════════

Step 1: VPS Setup (One Time)
├─ Install Docker
├─ Install Docker Compose
├─ Configure firewall (UFW)
└─ Configure SSH access

Step 2: Project Preparation
├─ Git clone repository
├─ Copy .env.production → .env
├─ Edit .env with real values
└─ Verify DNS configuration

Step 3: SSL Certificate (One Time)
├─ Run ./init-letsencrypt.sh
├─ Verify certificates created
└─ Certificates stored in ./certbot_data/

Step 4: Docker Build & Deploy
├─ docker-compose build
├─ docker-compose up -d
├─ Wait for services to start (health checks)
└─ Verify all services running: docker-compose ps

Step 5: Database Setup
├─ Migrations run automatically
├─ Create superuser: python manage.py createsuperuser
└─ Verify database health

Step 6: Verification
├─ curl https://pineriverapp.com/api/
├─ Check logs: docker-compose logs
├─ Visit admin: https://pineriverapp.com/admin/
└─ Run health-check.sh script

Step 7: Monitoring
├─ Set up log rotation
├─ Configure backups
├─ Monitor SSL renewal
└─ Regular health checks
```

---

**Architecture Version**: 1.0
**Last Updated**: January 2026
**Status**: Production Ready ✅
