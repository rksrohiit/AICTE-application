#!/usr/bin/env bash
set -e

# ==============================================================================
# init_ssl.sh — Automated SSL / HTTPS Certificate Provisioning
# Supports:
# 1. Real Let's Encrypt TLS Certificate via Certbot (for custom domains)
# 2. 2048-bit RSA Self-Signed Certificate fallback (for EC2 raw IP / localhost)
# ==============================================================================

DOMAIN="${1:-}"
EMAIL="${2:-admin@aicte.gov.in}"
SSL_DIR="./ssl"

mkdir -p "$SSL_DIR"

echo "========================================================"
echo "  AICTE Platform: Initializing SSL / HTTPS Certificates"
echo "========================================================"

if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "localhost" ]; then
    echo "[+] Domain specified: $DOMAIN"
    echo "[+] Attempting to obtain official Let's Encrypt certificate for $DOMAIN..."

    # Ensure port 80 is free for certbot standalone if nginx is not yet running
    if command -v certbot >/dev/null 2>&1; then
        certbot certonly --standalone \
            --preferred-challenges http \
            --agree-tos \
            --email "$EMAIL" \
            --non-interactive \
            -d "$DOMAIN" || true
        
        if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
            cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
            cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"
            echo "[✓] Official Let's Encrypt certificate acquired and installed in $SSL_DIR!"
            exit 0
        fi
    fi
    echo "[!] Certbot standalone acquisition bypassed or failed. Falling back to self-signed certificate."
fi

echo "[+] Generating 2048-bit RSA Self-Signed SSL Certificate for HTTPS..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/privkey.pem" \
    -out "$SSL_DIR/fullchain.pem" \
    -subj "/C=IN/ST=Delhi/L=New Delhi/O=AICTE/OU=Verification/CN=${DOMAIN:-localhost}" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "[✓] High-grade self-signed SSL certificate successfully generated in $SSL_DIR/"
echo "    - Private Key: $SSL_DIR/privkey.pem"
echo "    - Certificate: $SSL_DIR/fullchain.pem"
echo "    - Validity: 365 days"
echo "========================================================"
