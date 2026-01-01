#!/bin/bash

# Script to initialize Let's Encrypt SSL certificates for pineriverapp.com
# Run this once before starting the full docker-compose setup

set -e

DOMAIN="pineriverapp.com"
CERT_PATH="./certs"
EMAIL="admin@pineriverapp.com"  # Change this to your email

echo "==================================="
echo "Let's Encrypt SSL Certificate Setup"
echo "==================================="
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Check if Docker is running
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed or not in PATH"
    exit 1
fi

# Create necessary directories
mkdir -p ./nginx/ssl
mkdir -p ./certbot_data
mkdir -p ./certbot_www

echo "Step 1: Starting temporary Nginx container for ACME challenge..."
docker-compose up -d nginx 2>/dev/null || true

echo "Step 2: Waiting for Nginx to be ready..."
sleep 2

echo "Step 3: Running Certbot to obtain certificate..."
docker run --rm \
    --name certbot \
    -v ./certbot_data:/etc/letsencrypt \
    -v ./certbot_www:/var/www/certbot \
    -p 80:80 \
    certbot/certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

echo ""
echo "==================================="
echo "Certificate obtained successfully!"
echo "==================================="
echo ""
echo "Certificate location: ./certbot_data/live/$DOMAIN/"
echo ""
echo "Next steps:"
echo "1. Update your DNS records to point to your server IP (72.60.170.141)"
echo "2. Run: docker-compose down"
echo "3. Run: docker-compose up -d"
echo ""
echo "Your site will be available at:"
echo "  https://$DOMAIN"
echo "  https://www.$DOMAIN"
echo ""
