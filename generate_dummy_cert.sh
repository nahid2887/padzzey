#!/bin/bash

# Create dummy SSL certificates for initial nginx startup
# This allows nginx to start even without Let's Encrypt certificates

echo "Creating directories..."
mkdir -p ./certbot_data/live/pineriverapp.com/

echo "Generating self-signed certificate..."
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout ./certbot_data/live/pineriverapp.com/privkey.pem \
  -out ./certbot_data/live/pineriverapp.com/fullchain.pem \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=pineriverapp.com"

echo "Creating symbolic links..."
cd ./certbot_data/live/pineriverapp.com/
ln -sf fullchain.pem chain.pem
ln -sf fullchain.pem cert.pem

echo "✅ Dummy certificates created!"
echo ""
echo "Next steps:"
echo "1. Run: docker-compose up -d"
echo "2. Your site will be accessible via HTTPS (with browser warning)"
echo "3. Replace with real Let's Encrypt cert later when DNS is configured"
