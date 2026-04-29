# Setup & Installation Guide

This document covers everything you need to know to get the full Sakha platform up and running locally — including the main Product API, the Auth Microservice, and the Frontend — as well as how to seed the database with sample data.

---

## Prerequisites

- **Python 3.9+**
- **SurrealDB** — install via Homebrew:
  ```bash
  brew install surrealdb/tap/surreal
  ```

---

## Running Everything (Recommended)

The easiest way to start all three services at once is from the project root:

```bash
cd Sakha_Project
./start_all.sh
```

This script:
1. Starts SurrealDB on port 8000 (skips if already running).
2. Applies database indexes (`db_setup.surql`).
3. Creates Python venvs if missing and installs dependencies for both backends.
4. Starts the Main Product API on port 8080 with `--reload`.
5. Starts the Auth Microservice on port 8001 with `--reload`.
6. Starts the Frontend on port 3000 via Python's built-in HTTP server.

Once running, open **http://localhost:3000** in your browser.

To stop everything:
```bash
pkill -f 'surreal start'; pkill -f 'uvicorn'; pkill -f 'python3 -m http.server'
```

---

## Running Services Individually

### Main Product API

```bash
cd Sakha_Project/backend
./start.sh
```

This starts SurrealDB (port 8000) and the Product API (port 8080). To wipe the database and start fresh:
```bash
./start.sh --reset
```

Logs are written to `logs/surreal.log` and `logs/api.log`.

**Manual start:**

```bash
# Step 1 — Start SurrealDB
surreal start --log info --username root --password root \
  surrealkv://$(pwd)/surreal_data

# Step 2 — Apply indexes (first run only)
surreal sql -e http://localhost:8000 -u root -p root \
  --namespace sakha --database products < db_setup.surql

# Step 3 — Start FastAPI
source .venv/bin/activate
uvicorn main:app --reload --port 8080
```

### Auth Microservice

```bash
cd Sakha_Project/surreal-auth-api/backend
./start_auth.sh
```

This creates a venv if missing, installs dependencies, and starts the Auth API on port 8001.

**Manual start:**
```bash
cd Sakha_Project/surreal-auth-api/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd Sakha_Project
python3 -m http.server 3000
```

---

## Environment Variables

### Auth Microservice

Settings live in `surreal-auth-api/backend/.env`. Copy `.env.example` to get started.

| Variable | Default | Description |
|---|---|---|
| `SURREAL_URL` | `ws://localhost:8000/rpc` | SurrealDB WebSocket URL |
| `SURREAL_NAMESPACE` | `sakha` | SurrealDB namespace |
| `SURREAL_DB` | `products` | SurrealDB database name |
| `SURREAL_USERNAME` | `root` | SurrealDB username |
| `SURREAL_PASSWORD` | `root` | SurrealDB password |
| `APP_BASE_URL` | `http://localhost:8001` | Base URL used in verification email links |
| `FRONTEND_BASE_URL` | `http://localhost:3000` | Base URL used in password reset links |
| `PASSWORD_RESET_PATH` | `/?view=reset-password` | Path appended to `FRONTEND_BASE_URL` for reset links |
| `EMAIL_VERIFICATION_TTL_SECONDS` | `3600` | How long verification codes stay valid |
| `PASSWORD_RESET_TTL_SECONDS` | `1800` | How long password reset codes stay valid |
| `SMTP_HOST` | — | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP login username |
| `SMTP_PASSWORD` | — | SMTP login password |
| `SMTP_FROM` | — | From address for outgoing emails |
| `SMTP_USE_TLS` | `true` | Enable STARTTLS |
| `SMTP_USE_SSL` | `false` | Enable SSL (for port 465) |

---

## Verifying Services Are Running

```bash
# Main Product API
curl http://localhost:8080/health
# → {"status": "ok"}

# Auth Microservice — check the OpenAPI docs
open http://localhost:8001/docs

# Frontend
open http://localhost:3000
```

- **Product API base URL:** `http://localhost:8080/api/v1`
- **Product API Swagger UI:** `http://localhost:8080/docs`
- **Auth API base URL:** `http://localhost:8001`
- **Auth API Swagger UI:** `http://localhost:8001/docs`

---

## Seeding Sample Data

The seed script creates an admin user, brands, categories, and 20 sample products. The **Main Product API must be running** first.

```bash
# From the project root (Sakha_Project/)
python seed.py
```

To point at a non-default URL:
```bash
BASE_URL=http://localhost:9000 python seed.py
```

**Default admin credentials created by the seed:**
- Email: `admin@sakha.dev`
- Password: `sakha2026!`

> **Note:** The seed creates accounts directly in the Product API database. To create a user account through the Auth Microservice (the recommended path for the frontend), register via the sign-up form at `http://localhost:3000` and verify your email before logging in.
