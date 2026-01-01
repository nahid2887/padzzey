#!/bin/bash

# Pre-deployment checklist script
# Run this before deploying to production

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "======================================"
echo "  Pre-Deployment Checklist"
echo "======================================"
echo -e "${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Colors for status
check_success() {
    echo -e "${GREEN}✓${NC} $1"
}

check_error() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

echo -e "${BLUE}1. Environment Configuration${NC}"
echo "=================================="

if [ -f ".env" ]; then
    check_success ".env file exists"
    
    # Check required variables
    if grep -q "DEBUG=False" .env; then
        check_success "DEBUG is set to False"
    else
        check_error "DEBUG should be False for production"
    fi
    
    if grep -q "SECRET_KEY=" .env && ! grep -q "your-secret-key-here" .env; then
        check_success "SECRET_KEY is configured"
    else
        check_error "SECRET_KEY is not configured (check .env)"
    fi
    
    if grep -q "ALLOWED_HOSTS=" .env && grep -q "pineriverapp.com" .env; then
        check_success "ALLOWED_HOSTS includes pineriverapp.com"
    else
        check_error "ALLOWED_HOSTS should include pineriverapp.com"
    fi
    
    if grep -q "DB_PASSWORD=" .env && ! grep -q "your-secure-password-here" .env; then
        check_success "Database password is configured"
    else
        check_error "Database password is not secure"
    fi
else
    check_error ".env file not found (copy from .env.production)"
fi

echo ""
echo -e "${BLUE}2. Docker Configuration${NC}"
echo "=================================="

if [ -f "docker-compose.yml" ]; then
    check_success "docker-compose.yml exists"
    
    if grep -q "image: postgres:15" docker-compose.yml; then
        check_success "PostgreSQL service configured"
    else
        check_error "PostgreSQL service not found"
    fi
    
    if grep -q "image: redis:7-alpine" docker-compose.yml; then
        check_success "Redis service configured"
    else
        check_error "Redis service not found"
    fi
    
    if grep -q "nginx" docker-compose.yml; then
        check_success "Nginx service configured"
    else
        check_error "Nginx service not found"
    fi
    
    if grep -q "certbot/certbot" docker-compose.yml; then
        check_success "Certbot service configured"
    else
        check_error "Certbot service not found"
    fi
else
    check_error "docker-compose.yml not found"
fi

if [ -f "Dockerfile" ]; then
    check_success "Dockerfile exists"
else
    check_error "Dockerfile not found"
fi

echo ""
echo -e "${BLUE}3. Nginx Configuration${NC}"
echo "=================================="

if [ -f "nginx/nginx.conf" ]; then
    check_success "nginx.conf exists"
    
    if grep -q "pineriverapp.com" nginx/nginx.conf; then
        check_success "Domain configured in nginx.conf"
    else
        check_error "Domain not found in nginx.conf"
    fi
    
    if grep -q "ssl_certificate" nginx/nginx.conf; then
        check_success "SSL configuration found"
    else
        check_error "SSL configuration missing"
    fi
    
    if grep -q "gzip on" nginx/nginx.conf; then
        check_success "Gzip compression enabled"
    else
        check_warning "Gzip compression not enabled"
    fi
else
    check_error "nginx/nginx.conf not found"
fi

if [ -f "nginx/Dockerfile" ]; then
    check_success "nginx/Dockerfile exists"
else
    check_error "nginx/Dockerfile not found"
fi

echo ""
echo -e "${BLUE}4. Django Configuration${NC}"
echo "=================================="

if [ -f "pdezzy/pdezzy/settings.py" ]; then
    check_success "settings.py exists"
    
    if grep -q "os.getenv('ALLOWED_HOSTS'" pdezzy/pdezzy/settings.py; then
        check_success "ALLOWED_HOSTS reads from environment"
    else
        check_warning "ALLOWED_HOSTS should read from environment"
    fi
    
    if grep -q "pineriverapp.com" pdezzy/pdezzy/settings.py; then
        check_success "pineriverapp.com in CORS configuration"
    else
        check_error "pineriverapp.com not in CORS configuration"
    fi
else
    check_error "settings.py not found"
fi

echo ""
echo -e "${BLUE}5. SSL/Certificate Setup${NC}"
echo "=================================="

if [ -f "init-letsencrypt.sh" ]; then
    check_success "init-letsencrypt.sh exists"
    
    if [ -x "init-letsencrypt.sh" ]; then
        check_success "init-letsencrypt.sh is executable"
    else
        check_warning "init-letsencrypt.sh is not executable (run: chmod +x init-letsencrypt.sh)"
    fi
else
    check_error "init-letsencrypt.sh not found"
fi

echo ""
echo -e "${BLUE}6. Documentation${NC}"
echo "=================================="

DOCS=("PRODUCTION_DEPLOYMENT.md" "QUICKSTART.md" "SETUP_COMPLETE.md")

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        check_success "$doc exists"
    else
        check_warning "$doc not found"
    fi
done

echo ""
echo -e "${BLUE}7. System Requirements${NC}"
echo "=================================="

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    check_success "Docker installed: $DOCKER_VERSION"
else
    check_error "Docker is not installed"
fi

if command -v docker-compose &> /dev/null; then
    DC_VERSION=$(docker-compose --version)
    check_success "Docker Compose installed: $DC_VERSION"
else
    check_error "Docker Compose is not installed"
fi

if [ -d ".git" ]; then
    check_success "Git repository initialized"
else
    check_warning "Not a git repository"
fi

echo ""
echo -e "${BLUE}8. DNS & Domain${NC}"
echo "=================================="

echo "📝 Verify these DNS records exist:"
echo "   pineriverapp.com      A  72.60.170.141"
echo "   www.pineriverapp.com  A  72.60.170.141"
echo ""

if command -v nslookup &> /dev/null; then
    if nslookup pineriverapp.com 2>/dev/null | grep -q "72.60.170.141"; then
        check_success "DNS points to correct IP"
    else
        check_warning "DNS not yet updated (may take 24hrs)"
    fi
else
    check_warning "nslookup not available (install bind-utils)"
fi

echo ""
echo "======================================"
echo "  Summary"
echo "======================================"
echo -e "${GREEN}Passed: ✓${NC}"
echo -e "${RED}Errors: $ERRORS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Verify DNS is configured (wait if needed)"
    echo "2. Run: ./init-letsencrypt.sh"
    echo "3. Run: docker-compose up -d"
    echo "4. Verify: docker-compose ps"
    echo ""
else
    echo -e "${RED}✗ Please fix the errors above before deploying${NC}"
    exit 1
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Address warnings to avoid issues${NC}"
    echo ""
fi

echo "For detailed deployment guide, see: PRODUCTION_DEPLOYMENT.md"
echo "For quick start, see: QUICKSTART.md"
echo ""
