# AGENTS.md

## Quick Commands (all Docker-based)

- `make run` — start app + PostgreSQL (dev mode, auto-reload on `:8000`)
- `make stop` / `make clean` — stop / stop + remove volumes
- `make test-unit` — unit tests only (no DB needed)
- `make test-integration` — full-stack tests against real PostgreSQL (runs clean → run → test → clean)
- `make test` — both suites sequentially
- `make migrations msg='describe change'` — generate Alembic migration via Docker

All commands run inside Docker containers. There is no local dev setup without Docker.

## Architecture

Modular monolith organized by domain, not by technical layer. Three modules, each self-contained:

| Module | Entry | Key routes |
|--------|-------|------------|
| `app.modules.orders` | `models, schemas, routes, service, repository` | `GET/POST /orders/`, `PUT/DELETE /orders/{id}`, `POST /orders/{id}/cancel` |
| `app.modules.users` | same | `POST /users/register`, `POST /users/login` |
| `app.modules.payment` | same | `POST /payment/generate`, `POST /payment/pay/{order_id}`, `GET /payment/invoice/...`, `GET /payment/` |

- `app/api/router.py` — central router aggregating all module routers
- `app/core/config.py` — `Settings` singleton; `AUTH_JWT_SECRET_KEY` env var is **mandatory** (raises `ValueError` if missing)
- `app/core/auth.py` — JWT auth (HS256, 30min expiry); `get_current_user()` is a FastAPI dependency
- `app/db/session.py` — SQLAlchemy engine + `get_db()` generator dependency

### Order State Machine (non-obvious)

Strict FSM in `app.modules.orders.service.OrderStateMachine`. Invalid transitions raise `InvalidOrderTransition`:

```
RECEIVED → PROCESSING, CANCELLED
PROCESSING → FULFILLED, CANCELLED
FULFILLED → SHIPPED, CANCELLED
SHIPPED → DELIVERED
DELIVERED → (terminal)
CANCELLED → (terminal)
```

### Cross-module coupling

Payment depends on Orders (invoice generation advances order to PROCESSING; payment completion advances to FULFILLED). Orders depends on Payment (cancellation calls `cancel_invoice_by_order_id`). The `mark_invoice_paid_and_update_order()` method in the invoice repository updates both invoice and order atomically in a single transaction.

## Testing

- **Unit tests** (`tests/unit/`): Call service functions directly with `MagicMock` repos. No DB, no HTTP. Run via `make test-unit`.
- **Integration tests** (`tests/integration/`): Full `TestClient` + real PostgreSQL. `conftest.py` creates all tables before each test and drops them after. Runs via `make test-integration` which also manages container lifecycle.
- **Important**: `make test-integration` runs `clean → run → test → clean`. Do **not** run it while the app is already running — it will conflict with port 8000 and DB volumes.

### Test DB URL resolution

Integration tests use `TEST_DATABASE_URL` env var, falling back to `DATABASE_URL`, falling back to `postgresql://postgres:postgres@localhost:5432/test_db`. When running inside Docker via `docker-compose.unittests.yml`, `DATABASE_URL` is not set for unit tests (they don't need a DB). For local integration testing outside Docker, set `TEST_DATABASE_URL` or ensure PostgreSQL is running on `localhost:5432`.

## Alembic Migrations

- Run via Docker: `make migrations msg='describe change'`
- `alembic/env.py` uses `pkgutil.walk_packages('app.modules')` to auto-discover all model submodules for autogenerate — this is the **only** way Alembic sees all tables. Do not add `Base.metadata` imports manually.
- Models are in `app.modules.<name>.models`. After creating a new module, add its `models` submodule import or Alembic autogenerate will miss it.

## Environment

- `AUTH_JWT_SECRET_KEY` — **required** at startup. Set in `docker-compose.yml` as `test-secret-key-for-local-dev-only`.
- `DATABASE_URL` — PostgreSQL connection string. Default: `postgresql://postgres:postgres@localhost:5432/app`
- `DEBUG=true` — enables debug mode in docker-compose.

## Repo Conventions

- Routes are thin — all business logic goes in services.
- Services are thin — all data access goes in repositories.
- Pydantic schemas for all API contracts (input/output).
- `pytest.ini_options` sets `pythonpath = ["."]` and `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed.
- No linter/formatter/typechecker configured in `pyproject.toml` — none run in CI.
