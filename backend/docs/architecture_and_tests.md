# Architecture & Testing Overview

This document outlines the core technologies and project structure powering the Sakha Product API, as well as instructions on how to run its comprehensive test suite.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.111+ |
| Database | SurrealDB (async via `surrealdb` SDK) |
| Auth | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio + FastAPI TestClient |
| Runtime | Python 3.9+ |

---

## Project Structure

```
backend/
├── main.py                  # App entry point, router registration, lifespan
├── config.py                # All settings (env-driven via pydantic-settings)
├── auth.py                  # JWT helpers, FastAPI auth dependencies
├── database.py              # SurrealDB connection, DB wrapper class
├── storage.py               # File upload helpers (local disk / swap for S3)
├── start.sh                 # One-command start script (SurrealDB + FastAPI)
├── requirements.txt         # Python dependencies
├── db_setup.surql           # Index definitions — run once after DB creation
├── pytest.ini               # Test configuration
│
├── routers/                 # One file per domain area
│   ├── auth_router.py
│   ├── products.py
│   ├── variants.py
│   ├── inventory.py
│   ├── pricing.py
│   ├── categories.py
│   ├── attributes.py
│   ├── brands.py
│   ├── tags.py
│   ├── search.py
│   ├── cart.py
│   ├── coupons.py
│   ├── orders.py
│   ├── reviews.py
│   ├── qa.py
│   ├── wishlist.py
│   ├── bundles.py
│   ├── compare.py
│   ├── notifications.py
│   ├── analytics.py
│   ├── bulk.py
│   └── media.py
│
├── models/                  # Pydantic request/response schemas
│   ├── common.py            # Shared utilities: paginated(), strip_none(), Pagination
│   ├── product.py
│   ├── variant.py
│   ├── inventory.py
│   ├── cart.py
│   ├── order.py
│   ├── review.py
│   └── misc.py              # Auth, brands, categories, coupons, etc.
│
└── tests/
    ├── conftest.py          # MockDB, client fixtures (user/admin)
    └── test_*.py            # Comprehensive unit & route testing
```

---

## Running Tests

Tests use an in-memory `MockDB` — **no live SurrealDB connection is needed**.

```bash
cd Sakha_Project/backend

# Run all 202 tests
.venv/bin/python -m pytest

# Verbose output (shows each test name)
.venv/bin/python -m pytest -v

# Run a specific test file
.venv/bin/python -m pytest tests/test_auth.py -v
.venv/bin/python -m pytest tests/test_routes_products.py -v

# Run a single test by name
.venv/bin/python -m pytest -k "test_create_product_success" -v

# Stop on first failure
.venv/bin/python -m pytest -x
```

### Test coverage highlights

| Area | What it covers |
|---|---|
| **Core** | `strip_none`, `paginated`, `Pagination.to_surql`, `surreal_id`, `DB.count`, `DB.exists` |
| **Auth** | `hash_password`, JWT validation, `get_current_user`/`admin`, Login/Refresh routes |
| **Products** | Full product CRUD, lifecycle, SEO, shipping rates, locking, duplicate |
| **Orders/Cart** | Cart CRUD, merging, item management, placing orders, refunds, status updates |
| **Coupons** | Create, validate (expired, limit, min order edge cases) |
| **Reviews**| Submit, moderate, helpful marking, rating summary |

### How the test suite works

Route tests use FastAPI's `TestClient` with a `MockDB` dependency override. The `MockDB` uses `AsyncMock` for every database method, so each test configures exactly what the DB returns without needing a real connection.

Three client fixtures are available in `conftest.py`:
- **`client`** — unauthenticated
- **`user_client`** — regular user injected via dependency override
- **`admin_client`** — admin user injected, bypasses role checks
