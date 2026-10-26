# AICTE Platform — AWS EC2 HTTPS Deployment Guide

This guide provides end-to-end instructions for deploying the **AICTE AI-Powered Application Validation Platform** to an AWS EC2 instance with **HTTPS/SSL**, Docker, Nginx reverse proxy, and PostgreSQL.

---

## 📋 Architecture Overview

- **Reverse Proxy**: Nginx (terminates SSL on Port 443, redirects HTTP Port 80 -> 443)
- **SSL / TLS**: Automated Let's Encrypt / Certbot (for domain names) or RSA 2048-bit self-signed certificate (for raw EC2 IPs)
- **Frontend**: React + TypeScript (Vite production bundle served by Nginx)
- **Backend**: FastAPI (Python 3.11 with 4 Uvicorn workers)
- **Celery Worker**: Asynchronous OCR and heavy validation tasks
- **Databases**: PostgreSQL 15 & Redis 7
- **Object Storage**: MinIO S3-compatible document store
- **Mock Issuers**: Mock state & academic authority APIs for automated verification

---

## 🚀 Step 1: Launch an AWS EC2 Instance

1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2).
2. Click **Launch Instance** and configure:
   - **Name**: `aicte-validation-platform`
   - **AMI**: **Ubuntu Server 22.04 LTS (HVM)** or **Ubuntu Server 24.04 LTS** (64-bit x86)
   - **Instance Type**:
     - *Minimum*: `t3.medium` (2 vCPU, 4 GiB RAM)
     - *Recommended*: `t3.large` or `c6i.large` (for fast OCR & image processing)
   - **Key Pair**: Select your existing key pair (e.g. `dosje-key.pem` or create a new `.pem` key pair and download it).
   - **Network / Security Group**:
     - Check **Allow SSH traffic from anywhere** (Port `22`)
     - Check **Allow HTTP traffic from the internet** (Port `80`)
     - Check **Allow HTTPS traffic from the internet** (Port `443`)
   - **Storage**: At least **30 GiB** `gp3` SSD.
3. Click **Launch Instance**.
4. Note your instance's **Public IPv4 address** (e.g. `54.210.12.34`).

---

## 🔑 Step 2: Connect to your EC2 Instance via SSH

From your local machine (PowerShell, Command Prompt, or Terminal):

```bash
# Set key permissions (macOS / Linux)
chmod 400 dosje-key.pem

# SSH into the EC2 instance
ssh -i "path/to/your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

---

## 📦 Step 3: Clone the Repository & Run Automated Deployer

Once logged into your EC2 terminal:

```bash
# 1. Clone the repository
git clone https://github.com/rksrohiit/AICTE-application.git
cd AICTE-application

# 2. Make scripts executable
chmod +x deploy_ec2.sh scripts/init_ssl.sh

# 3. Option A: Deploy using your Domain Name (with trusted Let's Encrypt SSL)
sudo ./deploy_ec2.sh aicte.yourdomain.com admin@yourdomain.com

# 3. Option B: Deploy using EC2 Public IP (with self-signed SSL)
sudo ./deploy_ec2.sh
```

The script will automatically:
- Install Docker Engine, Docker Compose, Git, OpenSSL, and UFW firewall.
- Open ports `22`, `80`, and `443` in the firewall.
- Generate or acquire HTTPS SSL certificates.
- Build production multi-stage Docker images.
- Launch all 8 container services in background with automatic recovery.

---

## 🌐 Step 4: Verify Your Deployment

Open your web browser and navigate to:

| Endpoint | URL |
| :--- | :--- |
| **HTTPS Web Platform** | `https://<YOUR_EC2_PUBLIC_IP_OR_DOMAIN>/` |
| **Interactive API Docs** | `https://<YOUR_EC2_PUBLIC_IP_OR_DOMAIN>/docs` |
| **Backend Health Check** | `https://<YOUR_EC2_PUBLIC_IP_OR_DOMAIN>/api/v1/health` |
| **Mock Authority APIs** | `https://<YOUR_EC2_PUBLIC_IP_OR_DOMAIN>/mock-api/health` |

> [!NOTE]
> If accessing via raw EC2 IP (Option B), your browser will display a standard self-signed certificate notice (`Your connection is not private`). Click **Advanced -> Proceed to site**. When you attach a custom domain (Option A), Let's Encrypt provides a green padlock without warnings.

---

## 👤 Default Login Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **Scrutiny Officer** | `officer@aicte.gov.in` | `password123` |
| **Institution Registrar** | `registrar@bvcoe.edu.in` | `password123` |

---

## 🛠️ Management & Maintenance Commands

On your EC2 instance inside the repository directory:

```bash
# View live status of all services
sudo docker compose -f docker-compose.prod.yml ps

# View live container logs
sudo docker compose -f docker-compose.prod.yml logs -f

# View backend logs only
sudo docker compose -f docker-compose.prod.yml logs -f backend

# Restart services
sudo docker compose -f docker-compose.prod.yml restart

# Pull latest code and re-deploy
git pull origin main
sudo docker compose -f docker-compose.prod.yml up -d --build
```
