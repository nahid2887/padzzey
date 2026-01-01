#!/bin/bash

# Docker Compose Health Check Script
# Monitor the health of all services

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  Docker Services Health Check"
echo "======================================"
echo ""

# Check Docker is running
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker daemon is running${NC}"
echo ""

# Get compose project name
COMPOSE_PROJECT=${COMPOSE_PROJECT_NAME:-$(basename $(pwd))}

echo "Checking services..."
echo ""

# Function to check service
check_service() {
    local service=$1
    local container="${COMPOSE_PROJECT}_${service}_1"
    
    if docker ps --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
        local status=$(docker ps --filter "name=$service" --format "{{.Status}}" | head -1)
        echo -e "${GREEN}✓${NC} $service: $status"
        return 0
    else
        echo -e "${RED}✗${NC} $service: Not running"
        return 1
    fi
}

# Check each service
FAILED=0
check_service "nginx" || FAILED=1
check_service "web" || FAILED=1
check_service "db" || FAILED=1
check_service "redis" || FAILED=1
check_service "certbot" || FAILED=1

echo ""
echo "======================================"
echo "  Port Availability Check"
echo "======================================"
echo ""

# Check ports
check_port() {
    local port=$1
    local name=$2
    
    if ss -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✓${NC} Port $port ($name): In use"
    else
        echo -e "${YELLOW}⚠${NC} Port $port ($name): Not in use"
    fi
}

check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 8006 "Django"
check_port 5433 "PostgreSQL"
check_port 6380 "Redis"

echo ""
echo "======================================"
echo "  SSL Certificate Check"
echo "======================================"
echo ""

if [ -f "./certbot_data/live/pineriverapp.com/fullchain.pem" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in ./certbot_data/live/pineriverapp.com/fullchain.pem | cut -d= -f2)
    EXPIRY_SECONDS=$(date -d "$EXPIRY" +%s)
    CURRENT_SECONDS=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_SECONDS - $CURRENT_SECONDS) / 86400 ))
    
    if [ $DAYS_LEFT -gt 30 ]; then
        echo -e "${GREEN}✓${NC} SSL Certificate"
    elif [ $DAYS_LEFT -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} SSL Certificate expires in $DAYS_LEFT days"
    else
        echo -e "${RED}✗${NC} SSL Certificate is expired!"
    fi
    echo "  Expiry: $EXPIRY"
    echo "  Days remaining: $DAYS_LEFT"
else
    echo -e "${RED}✗${NC} SSL Certificate not found"
fi

echo ""
echo "======================================"
echo "  Disk Space Check"
echo "======================================"
echo ""

df -h | grep -E '^/dev/' | while read line; do
    USAGE=$(echo $line | awk '{print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 90 ]; then
        echo -e "${RED}✗${NC} $line"
    elif [ "$USAGE" -gt 80 ]; then
        echo -e "${YELLOW}⚠${NC} $line"
    else
        echo -e "${GREEN}✓${NC} $line"
    fi
done

echo ""
echo "======================================"
echo "  Service Logs Summary"
echo "======================================"
echo ""

# Recent errors in logs
ERRORS=$(docker-compose logs --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | tail -5)

if [ -z "$ERRORS" ]; then
    echo -e "${GREEN}✓ No recent errors in logs${NC}"
else
    echo -e "${YELLOW}Recent errors found:${NC}"
    echo "$ERRORS" | head -5
fi

echo ""
echo "======================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All systems operational!${NC}"
else
    echo -e "${RED}Some services are not running${NC}"
    echo "Run: docker-compose up -d"
fi
echo "======================================"
echo ""
