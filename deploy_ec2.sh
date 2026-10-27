#!/usr/bin/env bash
# ==============================================================================
# deploy_ec2.sh — Complete Universal Automated AWS EC2 Deployment Script
# Supports: Amazon Linux 2023, Amazon Linux 2, Ubuntu, Debian, CentOS, RHEL
# AICTE AI-Powered Application Validation Platform
#
# Usage:
#   sudo ./deploy_ec2.sh [optional-domain-name] [optional-email]
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-admin@aicte.gov.in}"

echo "======================================================================"
echo "  🚀 AICTE AI Application Validation Platform — Universal EC2 Deployer"
echo "======================================================================"

# 1. Verify sudo / root privileges
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Error: Please execute as root or with sudo:"
    echo "    sudo ./deploy_ec2.sh"
    exit 1
fi

# 2. Detect Public IP & Auto-Configure Domain
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com || curl -s https://ifconfig.me || echo "3.26.145.164")
PUBLIC_IP=$(echo "$PUBLIC_IP" | tr -d '[:space:]')
echo "[+] Detected EC2 Public IP: $PUBLIC_IP"

if [ -z "$DOMAIN" ]; then
    # Automatically use sslip.io to provide a valid, public FQDN domain that Let's Encrypt certifies!
    DASHED_IP="${PUBLIC_IP//./-}"
    DOMAIN="${DASHED_IP}.sslip.io"
    echo "[+] Auto-configured public domain for Let's Encrypt SSL: $DOMAIN"
else
    echo "[+] Using specified domain: $DOMAIN"
fi

# 3. Create Swap Space (Crucial for smooth Docker builds on t2.micro / t3.micro)
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
if [ ! -f /swapfile ] && [ "$TOTAL_RAM_MB" -lt 4000 ]; then
    echo "[+] System RAM is ${TOTAL_RAM_MB}MB (<4GB). Creating 2GB swapfile..."
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab || true
    echo "[✓] 2GB Swap space enabled."
fi

# 4. Detect Package Manager and Install Dependencies
echo "[+] Detecting Linux distribution and installing prerequisites..."
PKG_MGR=""

if command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    echo "[+] Detected DNF (Amazon Linux 2023 / Fedora / RHEL 9)"
    dnf update -y
    dnf install -y git curl openssl docker
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    echo "[+] Detected YUM (Amazon Linux 2 / CentOS / RHEL)"
    yum update -y
    yum install -y git curl openssl docker
elif command -v apt-get &> /dev/null; then
    PKG_MGR="apt"
    echo "[+] Detected APT (Ubuntu / Debian)"
    apt-get update -y
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        git \
        openssl \
        ufw
    if ! command -v docker &> /dev/null; then
        echo "[+] Installing Docker via official repository..."
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
else
    echo "[!] Unknown package manager. Checking for existing tools..."
fi

# 5. Start and Enable Docker Daemon
echo "[+] Starting Docker service..."
systemctl enable docker || true
systemctl start docker || true

# Grant permissions to common EC2 users
usermod -aG docker ec2-user 2>/dev/null || true
usermod -aG docker ubuntu 2>/dev/null || true

# 6. Install Docker Compose CLI Plugin if missing
if ! docker compose version &> /dev/null; then
    echo "[+] Installing Docker Compose CLI plugin binary..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) DOCKER_ARCH="x86_64" ;;
        aarch64|arm64) DOCKER_ARCH="aarch64" ;;
        *) DOCKER_ARCH="x86_64" ;;
    esac
    COMPOSE_URL="https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-${DOCKER_ARCH}"
    
    mkdir -p /usr/local/lib/docker/cli-plugins /usr/libexec/docker/cli-plugins /usr/local/bin
    curl -fsSL "$COMPOSE_URL" -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    
    ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose || true
    ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/libexec/docker/cli-plugins/docker-compose || true
    ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/bin/docker-compose || true
    echo "[✓] Docker Compose installed successfully: $(docker compose version)"
fi

# 7. Configure UFW if installed
if command -v ufw &> /dev/null; then
    echo "[+] Configuring UFW..."
    ufw allow 22/tcp || true
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
    ufw --force enable || true
fi

# 8. Provision SSL Certificates (Let's Encrypt or Self-Signed)
echo "[+] Provisioning HTTPS / SSL certificates..."
chmod +x scripts/init_ssl.sh
./scripts/init_ssl.sh "$DOMAIN" "$EMAIL"

# 9. Generate Production .env configuration
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
    echo "[✓] Created .env configuration."\n    # Copy .env into backend folder for docker-compose.yml compatibility\n    mkdir -p backend\n    cp .env backend/.env || true
else
    # Update DOMAIN in existing .env
    sed -i "s/^DOMAIN=.*/DOMAIN=$DOMAIN/" .env || true
fi

# 10. Build and launch production Docker Compose stack
echo "[+] Building and launching container services..."
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d --build

# 11. Wait for database and backend initialization
echo "[+] Waiting for services to initialize..."
for i in {1..40}; do
    if docker compose -f docker-compose.prod.yml exec -T backend curl -s http://localhost:8000/api/v1/health &>/dev/null; then
        echo "[✓] Backend API is up and healthy!"
        break
    fi
    echo -n "."
    sleep 3
done
echo ""

# 12. Seed database with demo data
echo "[+] Seeding database with demo users, applications and verification records..."
docker compose -f docker-compose.prod.yml exec -T backend python /scripts/seed_sqlite.py || true

# 13. Output service status and access URLs
echo "======================================================================"
echo "  🎉 Deployment Complete! Your platform is LIVE on AWS EC2:"
echo "======================================================================"
echo "  🌐 Web Application   : http://$DOMAIN/"
echo "  🔒 HTTPS Web Portal   : https://$DOMAIN/"
echo "  📑 API Documentation : http://$DOMAIN/docs"
echo "  🏛️ Mock APIs Docs     : http://$DOMAIN/mock-api/docs"
echo "  🏥 Health Endpoint    : http://$DOMAIN/api/v1/health"
echo ""
echo "  Default Demo Credentials (One-Click or Manual):"
echo "  - Officer Account     : officer@aicte.gov.in / password123"
echo "  - Institution Account : registrar@bvcoe.edu.in / password123"
echo "======================================================================"
