```
  ╔═══════════════════════════════════════════════════════════════════╗
  ║                                                                   ║
  ║   Developed with Claude Code initially, then moved to Open Code   ║
  ║   --- but using a local model Qwen3.6-35B-A3B via llama.cpp ---   ║
  ║                                                                   ║
  ╚═══════════════════════════════════════════════════════════════════╝
```

# Order Management System API

A lightweight, modular FastAPI application for order management.

Built as a modular monolith, the project organizes code by domain (e.g., `orders`, `users`) rather than by technical layers alone.
It uses PostgreSQL for data storage, Alembic for schema migrations, and SQLite for fast, isolated unit tests.
The application is containerized with Docker for consistent local development and deployment.

> **This structure keeps concerns well-defined in a monolithic codebase while encouraging boundaries
> that translate well to microservices, without introducing that complexity prematurely.**

## Architecture

The codebase follows a domain-oriented structure combined with the **Service Layer** and **Repository** patterns.
Each module (e.g., `orders`, `users`) is self-contained and implements a consistent internal layout:

| Layer          | Responsibility                                                     |
| -------------- | ------------------------------------------------------------------ |
| **routes**     | HTTP interface (request/response handling, validation entrypoints) |
| **service**    | Business logic and orchestration (Service Layer pattern)           |
| **repository** | Data access abstraction over the database                          |
| **models**     | Database models (ORM entities)                                     |
| **schemas**    | API contracts (input/output validation and serialization)          |

**Key characteristics:**
* Thin controllers: Routes delegate all non-trivial logic to services
* Explicit business layer: Services centralize rules and workflows
* Decoupled data access: Repositories isolate database interactions
* Domain isolation: Each module is self-contained, reducing cross-coupling
* Testability: Business logic can be tested independently of HTTP and database layers

The design prioritizes clarity, testability, and maintainability,
while remaining flexible enough to evolve into a distributed architecture if needed.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)

## Run the Application

```bash
make run
```

This will spin up two containers:
- PostgreSQL
- Application in development mode with auto-reload and debug

API will be available at:
```
http://localhost:8000
```
Swagger UI at:
```
http://localhost:8000/docs
```

## Running Tests

```bash
# Run unit tests
make test-unit
# Run integration tests
make test-integration
```

## Example API Usage

```bash
# Create Order
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"item": "laptop"}'

# Get Order
curl http://localhost:8000/orders/1

# List Orders
curl http://localhost:8000/orders/
```

## All Make Targets

| Command | Description |
|---------|-------------|
| `make help` | List all available commands |
| `make build` | Build the Docker container |
| `make run` | Run the app (development with auto-reload) |
| `make stop` | Stop the app |
| `make clean` | Clean up Docker containers and volumes |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests |
| `make test-integration` | Run integration tests |
| `make migrations msg=<msg>` | Generate alembic migrations |
