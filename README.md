# AICTE AI-Powered Validation Platform

> **Smart Hackathon Initiative (SIH) Project**  
> An intelligent, AI-driven document validation and approval workflow platform for AICTE (All India Council for Technical Education).

---

## 📋 Table of Contents

- [About](#about)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Service URLs](#service-urls)
- [Demo Accounts](#demo-accounts)
- [Architecture Overview](#architecture-overview)
- [API Documentation](#api-documentation)
- [Sprint Status](#sprint-status)
- [License](#license)

---

## About

The AICTE AI-Powered Validation Platform automates the tedious, error-prone process of manually reviewing institutional applications (EOA renewals, new approvals, etc.). It uses OCR, NLP-based field extraction, a YAML-driven rules engine, and AI-assisted consistency checking to reduce review time from weeks to hours.

Key capabilities:
- **Automated document ingestion** via MinIO object storage
- **OCR + AI field extraction** for 8+ document types
- **Rules engine** powered by declarative YAML rule definitions
- **External API verification** (DigiLocker, NAAC, State NOC, Fire Dept.)
- **Role-based workflow** — Institution → Scrutiny Officer → Senior Officer
- **Real-time task tracking** via Celery + Redis
- **Audit trail** with full decision history

---

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| [Docker](https://docs.docker.com/get-docker/) | 24.x |
| [Docker Compose](https://docs.docker.com/compose/install/) | 2.x (plugin) |
| Git | 2.x |

> **Note:** No local Python or Node.js installation is required — everything runs inside containers.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/aicte-validation-platform.git
cd aicte-validation-platform

# 2. Copy environment template and configure secrets
cp backend/.env.example backend/.env

# 3. Build and start all services
docker compose up --build
```

The platform will be available at **http://localhost** (via Nginx reverse proxy) once all health checks pass.

To seed demo data after first start:

```bash
docker compose exec backend python /app/scripts/seed_demo.py
```

---

## Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | http://localhost:3000 | React + Vite SPA |
| **Backend API** | http://localhost:8000 | FastAPI |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API explorer |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative docs UI |
| **MinIO Console** | http://localhost:9001 | Object storage admin |
| **Mock Issuer APIs** | http://localhost:8001 | External API simulator |
| **Nginx Gateway** | http://localhost | Production-like proxy |

---

## Demo Accounts

All demo accounts use the password: **`Demo@1234`**

| Role | Email | Description |
|------|-------|-------------|
| **Institution** | institution@demo.com | Submits applications and uploads documents |
| **Scrutiny Officer** | officer@demo.com | Reviews and validates applications |
| **Senior Officer** | senior@demo.com | Final approval authority; can override decisions |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          NGINX (Port 80)                         │
│              Reverse Proxy + WebSocket + Gzip                    │
└────────────┬────────────────────────┬────────────────────────────┘
             │                        │
    ┌────────▼────────┐    ┌──────────▼──────────┐
    │  Frontend        │    │  Backend (FastAPI)   │
    │  React + Vite    │    │  REST API + WebSocket│
    │  Port 3000       │    │  Port 8000           │
    └─────────────────┘    └──────────┬───────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
    ┌─────────▼──────┐    ┌──────────▼──────┐    ┌──────────▼──────┐
    │  PostgreSQL 15  │    │   Redis 7        │    │   MinIO          │
    │  Primary DB     │    │   Cache + Queue  │    │   Object Storage │
    │  Port 5432      │    │   Port 6379      │    │   Port 9000/9001 │
    └────────────────┘    └─────────┬───────┘    └────────────────┘
                                    │
                          ┌─────────▼───────┐
                          │  Celery Worker   │
                          │  Async Tasks     │
                          │  (OCR, AI, Rules)│
                          └─────────────────┘
                                    │
                          ┌─────────▼───────┐
                          │  Mock Issuer APIs│
                          │  DigiLocker /    │
                          │  NAAC / State NOC│
                          │  Port 8001       │
                          └─────────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React 18, Vite, TailwindCSS, shadcn/ui | User interface |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 | REST API |
| Task Queue | Celery + Redis | Background OCR, validation, AI tasks |
| Database | PostgreSQL 15 | Persistent data store |
| Object Storage | MinIO (S3-compatible) | Document file storage |
| OCR | pytesseract / pdf2image | Text extraction from documents |
| AI | Google Gemini API (configurable) | Field extraction, consistency checks |
| Rules Engine | PyYAML + custom engine | Declarative validation rules |
| Auth | JWT (access + refresh tokens) | Authentication and authorization |

---

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs  
  Full interactive explorer — try out endpoints directly from the browser.

- **ReDoc**: http://localhost:8000/redoc  
  Clean, readable documentation format.

- **OpenAPI JSON**: http://localhost:8000/openapi.json  
  Machine-readable schema for client generation.

---

## Sprint Status

| Sprint | Title | Status |
|--------|-------|--------|
| **Sprint 1** | Project scaffold, DB models, Auth, MinIO, Celery setup | ✅ Complete |
| **Sprint 2** | Document upload, OCR pipeline, field extraction | 🔄 In Progress |
| **Sprint 3** | Rules engine, validation scoring, flag generation | 🔄 In Progress |
| **Sprint 4** | External API verification (DigiLocker, NAAC, etc.) | 🔄 In Progress |
| **Sprint 5** | Review workflow, officer dashboard, audit trail | 🔄 In Progress |
| **Sprint 6** | Frontend integration, demo seeding, E2E testing | 🔄 In Progress |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

> Built with ❤️ for Smart India Hackathon (SIH)
