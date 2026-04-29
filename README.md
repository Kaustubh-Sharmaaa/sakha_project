# Sakha Project

A full-featured e-commerce platform built with **FastAPI**, **SurrealDB**, and a vanilla JS frontend, running as four Dockerised services.

| Service | URL | Description |
|---|---|---|
| Frontend | `http://localhost` | Vanilla JS / HTML storefront |
| Product API | `http://localhost:8080` | Products, cart, orders, reviews, coupons, analytics |
| Auth Microservice | `http://localhost:8001` | Registration, login, email verification, password reset |
| SurrealDB | internal | Database (not exposed publicly) |

The frontend's nginx reverse-proxies `/api/` → product-api and `/auth/` → auth-api, so the UI only ever talks to `http://localhost`.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

---

## Quick start

**1. Clone the repo**
```bash
git clone https://github.com/Kaustubh-Sharmaaa/sakha_project.git
cd sakha_project
```

**2. Create the `.env` files**
```bash
cp backend/.env.example backend/.env
cp surreal-auth-api/backend/.env.example surreal-auth-api/backend/.env
```

Edit both files and set at minimum:
- `SECRET_KEY` — generate one with `openssl rand -hex 32`
- SMTP credentials in `surreal-auth-api/backend/.env` if you want email verification

The default SurrealDB credentials (`root`/`root`) work out of the box for local development.

**3. Start everything**
```bash
docker compose up --build
```

Open **http://localhost** in your browser.

---

## Stopping

```bash
# Stop containers, keep DB data
docker compose down

# Stop containers and wipe the DB volume (fresh start)
docker compose down -v
```

---

## Running the tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

> The test suite uses mocks and does not require Docker to be running.

---

## Documentation

- **[Setup Guide](backend/docs/setup_guide.md)** — local dev (non-Docker) setup
- **[API Reference](backend/docs/api_reference.md)** — all endpoints, request/response shapes, error codes
- **[Architecture & Tests](backend/docs/architecture_and_tests.md)** — tech stack, project structure, test strategy
