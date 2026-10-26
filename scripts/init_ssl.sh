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

    # Try Certbot directly or via Docker
    if command -v certbot >/dev/null 2>&1; then
        certbot certonly --standalone \
            --preferred-challenges http \
            --agree-tos \
            --email "$EMAIL" \
            --non-interactive \
            -d "$DOMAIN" || true
        
        if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
            cp -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
            cp -f "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"
            echo "[✓] Official Let's Encrypt certificate acquired and installed in $SSL_DIR!"
            exit 0
        fi
    elif command -v docker >/dev/null 2>&1; then
        echo "[+] Requesting verified Let's Encrypt SSL certificate for $DOMAIN via Docker Certbot..."
        mkdir -p "$SSL_DIR/letsencrypt"
        docker run --rm -p 80:80 \
            -v "$(pwd)/$SSL_DIR/letsencrypt:/etc/letsencrypt" \
            certbot/certbot certonly \
            --standalone \
            --preferred-challenges http \
            --agree-tos \
            --register-unsafely-without-email \
            --non-interactive \
            -d "$DOMAIN" || true
        
        CERT_LIVE="$SSL_DIR/letsencrypt/live/$DOMAIN"
        if [ -f "$CERT_LIVE/fullchain.pem" ]; then
            cp -f "$CERT_LIVE/fullchain.pem" "$SSL_DIR/fullchain.pem"
            cp -f "$CERT_LIVE/privkey.pem" "$SSL_DIR/privkey.pem"
            echo "[✓] Official Let's Encrypt certificate acquired and installed in $SSL_DIR!"
            exit 0
        fi
    fi
    echo "[!] Certbot standalone acquisition bypassed or failed. Falling back to self-signed certificate."
fi

echo "[+] Generating 2048-bit RSA Self-Signed SSL Certificate for HTTPS..."
OPENSSL_CNF=$(mktemp)
cat <<EOF > "$OPENSSL_CNF"
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = IN
ST = Delhi
L = New Delhi
O = AICTE
OU = Verification
CN = ${DOMAIN:-localhost}

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

if [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "IP.2 = $DOMAIN" >> "$OPENSSL_CNF"
else
    echo "DNS.2 = ${DOMAIN:-localhost}" >> "$OPENSSL_CNF"
fi

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/privkey.pem" \
    -out "$SSL_DIR/fullchain.pem" \
    -config "$OPENSSL_CNF"
rm -f "$OPENSSL_CNF"

echo "[✓] High-grade self-signed SSL certificate successfully generated in $SSL_DIR/"
echo "    - Private Key: $SSL_DIR/privkey.pem"
echo "    - Certificate: $SSL_DIR/fullchain.pem"
echo "    - Validity: 365 days"
echo "========================================================"
