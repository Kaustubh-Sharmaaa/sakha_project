# Architecture & Testing Overview

This document outlines the core technologies and project structure powering the Sakha platform — including both the Main Product API and the Auth Microservice — as well as instructions on how to run each test suite.

---

## Tech Stack

### Main Product API

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.111+ |
| Database | SurrealDB (async via `surrealdb` SDK) |
| Auth | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio + FastAPI TestClient |
| Runtime | Python 3.9+ |

### Auth Microservice

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Database | SurrealDB (sync via `surrealdb` SDK) |
| Auth | JWT (python-jose) + pbkdf2_sha256 (passlib) |
| Validation | Pydantic v2 |
| Email | SMTP via smtplib |
| Testing | pytest + FastAPI TestClient |
| Runtime | Python 3.9+ |

### Frontend

| Layer | Technology |
|---|---|
| Language | Vanilla JavaScript (ES2022) |
| Markup | HTML5 |
| Styles | CSS custom properties + `oklch` colour space |
| HTTP | Native `fetch` API |
| Served by | Python `http.server` (port 3000) |

---

## Project Structure

### Main Product API

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

### Auth Microservice

```
surreal-auth-api/backend/
├── start_auth.sh            # One-command start script (port 8001)
├── requirements.txt         # Python dependencies
├── .env                     # Local environment config (SMTP, SurrealDB, TTLs)
│
├── app/
│   ├── main.py              # App entry point, lifespan, CORS middleware
│   ├── routers/
│   │   └── auth_router.py   # All /auth/* endpoints
│   ├── services/
│   │   ├── auth_service.py  # Business logic: create_user, authenticate_user, get_me, etc.
│   │   └── email_service.py # SMTP email sending
│   ├── schemas/
│   │   └── user.py          # Pydantic schemas: UserCreate, UserLogin, ResetPassword, etc.
│   ├── core/
│   │   ├── config.py        # Settings loaded from .env
│   │   └── security.py      # JWT creation/decoding, password hashing, token hashing
│   └── db/
│       └── surreal.py       # SurrealDB connection and connect() helper
│
└── tests/
    ├── conftest.py          # sys.path setup
    ├── test_auth_router.py  # HTTP endpoint tests (11 tests)
    └── test_auth_service.py # Service-layer unit tests (10 tests)
```

### Frontend

```
Sakha_Project/
├── index.html               # Single-page app shell — auth screen + storefront
├── app.js                   # All JS: auth flows, product browsing, cart, wishlist
├── style.css                # All styles
└── start_all.sh             # Starts all three services
```

---

## Frontend ↔ API Routing

The frontend uses two separate base URLs, kept in `CONFIG` at the top of `app.js`:

| Constant | Value | Used for |
|---|---|---|
| `CONFIG.API` | `http://localhost:8080/api/v1` | Products, cart, orders, search, reviews, coupons |
| `CONFIG.AUTH_API` | `http://localhost:8001` | All auth flows via `authApi` helper |

All calls to `authApi` go to the Auth Microservice; all calls to `api` go to the Main Product API.

---

## Running the Main Product API Tests

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
| **Reviews** | Submit, moderate, helpful marking, rating summary |

### How the test suite works

Route tests use FastAPI's `TestClient` with a `MockDB` dependency override. The `MockDB` uses `AsyncMock` for every database method, so each test configures exactly what the DB returns without needing a real connection.

Three client fixtures are available in `conftest.py`:
- **`client`** — unauthenticated
- **`user_client`** — regular user injected via dependency override
- **`admin_client`** — admin user injected, bypasses role checks

---

## Running the Auth Microservice Tests

Tests use monkeypatching — **no live SurrealDB connection or SMTP server is needed**.

```bash
cd Sakha_Project/surreal-auth-api/backend

# Run all 21 tests
python3 -m pytest

# Verbose output
python3 -m pytest -v

# Run a specific file
python3 -m pytest tests/test_auth_router.py -v
python3 -m pytest tests/test_auth_service.py -v

# Run a single test by name
python3 -m pytest -k "test_login_unverified_email_returns_403" -v
```

### Test coverage highlights

| Area | What it covers |
|---|---|
| **Router** | Signup, login (valid / wrong password / unverified email), refresh, email verification, password reset (request / verify / confirm), logout |
| **Service** | `create_user` (DB write + email send), `verify_email_code`, `authenticate_user` (success + unverified guard), `refresh_access_token`, `logout_user` session revocation, `reset_pass_request`, `verify_reset_pass_code` (used/expired), `reset_pass` (mismatch + success) |

### How the test suite works

Router tests use FastAPI's `TestClient` with `monkeypatch` to replace service-layer functions, keeping them focused on HTTP contract (status codes and response shapes) without touching business logic.

Service tests use a `_FakeDB` class that replays pre-queued responses, allowing full logic paths to be exercised without a real SurrealDB instance. SMTP calls are replaced with a `sent` dict capture.
