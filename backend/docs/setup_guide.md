# Setup & Installation Guide

This document covers everything you need to know to get the Sakha Product API up and running locally, as well as how to seed the initial database with sample data.

---

## Prerequisites

- **Python 3.9+**
- **SurrealDB** — install via Homebrew:
  ```bash
  brew install surrealdb/tap/surreal
  ```

---

## Installation

```bash
# Clone / navigate to the project
cd Sakha_Project/backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the API

### Option A — One-command start script (recommended)

```bash
cd Sakha_Project/backend
./start.sh
```

This script:
1. Starts SurrealDB on port 8000 (skips if already running).
2. Applies database indexes (`db_setup.surql`).
3. Creates the Python venv if missing and installs dependencies.
4. Starts FastAPI on port 8080 with `--reload`.

To **wipe the database** and start fresh:
```bash
./start.sh --reset
```

Logs are written to `logs/surreal.log` and `logs/api.log`.

### Option B — Manual start

**Step 1 — Start SurrealDB:**
```bash
surreal start --log info --username root --password root \
  surrealkv://$(pwd)/surreal_data
```

**Step 2 — Apply indexes (first run only):**
```bash
surreal sql -e http://localhost:8000 -u root -p root \
  --namespace sakha --database products < db_setup.surql
```

**Step 3 — Start FastAPI:**
```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8080
```

---

## Verifying It's Running

```bash
curl http://localhost:8080/health
# → {"status": "ok"}
```

- **API base URL:** `http://localhost:8080/api/v1`
- **Interactive docs (Swagger UI):** `http://localhost:8080/docs`
- **Alternative docs (ReDoc):** `http://localhost:8080/redoc`

To stop the services:
```bash
pkill -f "surreal start"
pkill -f "uvicorn main:app"
```

---

## Seeding Sample Data

The seed script creates an admin user, brands, categories, and 20 sample products. The backend **must be running** first.

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
