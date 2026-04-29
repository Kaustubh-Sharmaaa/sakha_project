# Sakha Product API

A full-featured e-commerce platform built with **FastAPI**, **SurrealDB**, and a vanilla JS frontend. The project is composed of three services that run together:

| Service | URL | Description |
|---|---|---|
| Main Product API | `http://localhost:8080` | Products, cart, orders, reviews, coupons, analytics, and more |
| Auth Microservice | `http://localhost:8001` | Registration, login, email verification, password reset, session management |
| Frontend | `http://localhost:3000` | Vanilla JS / HTML storefront — consumes both APIs |

Run everything with a single command:
```bash
./start_all.sh
```

---

## Documentation Directory

We have broken down the documentation into focused guides to make it easier to digest:

1. **[Setup & Installation Guide](backend/docs/setup_guide.md)**
   Everything you need to know about getting your local environment up and running, starting all three services together or individually, and seeding the database.

2. **[API Reference & Integration](backend/docs/api_reference.md)**
   Extensive documentation covering all capabilities of both REST APIs. Contains details on the auth microservice endpoints, authentication workflows, route configurations, data shapes, error codes, and the entire backend functionality ecosystem (from Auth & Products to Cart & Orders).

3. **[Architecture & Testing](backend/docs/architecture_and_tests.md)**
   Information regarding our technical stack, detailed project structure map for both backends, and instructions on how to navigate and execute the test suites for both the main API and the auth microservice.
