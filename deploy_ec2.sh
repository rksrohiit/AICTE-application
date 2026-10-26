#!/usr/bin/env bash
# ==============================================================================
# deploy_ec2.sh — Complete Automated AWS EC2 Deployment Script
# AICTE AI-Powered Application Validation Platform
#
# Usage:
#   chmod +x deploy_ec2.sh
#   sudo ./deploy_ec2.sh [optional-domain-name] [optional-email]
#
# Example:
#   sudo ./deploy_ec2.sh aicte.example.com admin@example.com
#   sudo ./deploy_ec2.sh  # (Deploys using Public IP with Self-Signed HTTPS)
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-admin@aicte.gov.in}"

echo "======================================================================"
echo "  🚀 AICTE AI Application Validation Platform — AWS EC2 Deployer"
echo "======================================================================"

# 1. Verify sudo / root privileges
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Error: Please execute as root or with sudo:"
    echo "    sudo ./deploy_ec2.sh $DOMAIN $EMAIL"
    exit 1
fi

# Detect Public IP
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com || curl -s https://ifconfig.me || echo "localhost")
echo "[+] Detected EC2 Public IP: $PUBLIC_IP"
if [ -z "$DOMAIN" ]; then
    DOMAIN="$PUBLIC_IP"
    echo "[+] No custom domain specified. Using Public IP: $DOMAIN"
fi

# 2. System updates & install prerequisites
echo "[+] Updating system packages and installing prerequisites..."
apt-get update -y
apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    openssl \
    ufw

# 3. Install Docker and Docker Compose (if not already installed)
if ! command -v docker &> /dev/null; then
    echo "[+] Installing Docker Engine..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "[✓] Docker installed successfully."
fi

# 4. Configure EC2 Firewall (UFW)
echo "[+] Configuring EC2 Firewall..."
ufw allow 22/tcp || true   # SSH
ufw allow 80/tcp || true   # HTTP (Certbot ACME challenge / redirect)
ufw allow 443/tcp || true  # HTTPS (TLS)
ufw --force enable || true

# 5. Provision SSL Certificates (Let's Encrypt or Self-Signed)
echo "[+] Provisioning HTTPS / SSL certificates..."
chmod +x scripts/init_ssl.sh
./scripts/init_ssl.sh "$DOMAIN" "$EMAIL"

# 6. Generate Production .env configuration
if [ ! -f ".env" ]; then
    echo "[+] Generating production .env configuration..."
    JWT_SECRET=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    MINIO_PASSWORD=$(openssl rand -hex 16)

    cat <<EOF > .env
DOMAIN=$DOMAIN
POSTGRES_USER=aicte
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=aicte_db
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$MINIO_PASSWORD
JWT_SECRET_KEY=$JWT_SECRET
EOF
    echo "[✓] Created .env with cryptographically secure random secrets."
fi

# 7. Build and launch production Docker Compose stack
echo "[+] Building and launching container services..."
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d --build

# 8. Health checks and verification
echo "[+] Waiting 15 seconds for containers to initialize..."
sleep 15

echo "[+] Checking running services..."
docker compose -f docker-compose.prod.yml ps

echo "======================================================================"
echo "  🎉 Deployment Complete! Your platform is live on AWS EC2:"
echo "======================================================================"
echo "  🌐 HTTPS Web Portal : https://$DOMAIN/"
echo "  📑 API Documentation: https://$DOMAIN/docs"
echo "  🏥 Backend Health   : https://$DOMAIN/api/v1/health"
echo "  🏛️ Mock APIs Health : https://$DOMAIN/mock-api/health"
echo ""
echo "  Default Demo Credentials:"
echo "  - Officer Account     : officer@aicte.gov.in / password123"
echo "  - Institution Account : registrar@bvcoe.edu.in / password123"
echo "======================================================================"
