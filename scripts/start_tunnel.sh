#!/usr/bin/env bash
# ==============================================================================
# start_tunnel.sh — Cloudflare Tunnel for Verified HTTPS (Zero SSL Warnings)
# Provides an instant, publicly-trusted HTTPS URL with green padlock.
#
# Usage: sudo ./scripts/start_tunnel.sh
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "  🔒 AICTE Platform — Cloudflare Secure Tunnel Setup"
echo "======================================================================"

# 1. Install cloudflared if not present
if ! command -v cloudflared &> /dev/null; then
    echo "[+] Installing Cloudflare Tunnel (cloudflared)..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64) CF_ARCH="amd64" ;;
        aarch64|arm64) CF_ARCH="arm64" ;;
        *) CF_ARCH="amd64" ;;
    esac
    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
    curl -fsSL "$CF_URL" -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    echo "[✓] cloudflared installed successfully."
fi

# 2. Ensure containers are running
if docker compose -f docker-compose.prod.yml ps --services --filter "status=running" 2>/dev/null | grep -q backend; then
    echo "[✓] Docker services are already running."
else
    echo "[+] Starting Docker services first..."
    docker compose -f docker-compose.prod.yml up -d --build
    echo "[+] Waiting 20 seconds for services to initialize..."
    sleep 20
fi

# 3. Start the Cloudflare tunnel pointing to the local Nginx on port 80
echo ""
echo "======================================================================"
echo "  🚀 Starting Cloudflare Secure Tunnel..."
echo "  Your verified HTTPS URL will appear below in a few seconds."
echo "  Press Ctrl+C to stop the tunnel."
echo "======================================================================"
echo ""

cloudflared tunnel --url http://localhost:80 2>&1 | tee /tmp/cloudflared.log &
TUNNEL_PID=$!

# 4. Wait for the tunnel URL to appear in the output
for i in {1..30}; do
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1 || true)
    if [ -n "$TUNNEL_URL" ]; then
        echo ""
        echo "======================================================================"
        echo "  🎉 Your Verified Secure HTTPS Portal is LIVE!"
        echo "======================================================================"
        echo ""
        echo "  🔒 Secure URL  : $TUNNEL_URL"
        echo "  📑 API Docs    : $TUNNEL_URL/docs"
        echo "  🏛️  Mock APIs   : $TUNNEL_URL/mock-api/docs"
        echo ""
        echo "  ✅ 100% Trusted SSL — Green padlock in all browsers"
        echo "  ✅ No security warnings — Signed by Cloudflare CA"
        echo ""
        echo "  Demo Credentials:"
        echo "  - Officer  : officer@aicte.gov.in / password123"
        echo "  - Institution : registrar@bvcoe.edu.in / password123"
        echo "======================================================================"
        echo ""
        echo "  Press Ctrl+C to stop the tunnel."
        break
    fi
    sleep 2
done

# Keep alive
wait $TUNNEL_PID
