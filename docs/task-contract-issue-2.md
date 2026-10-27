# Task contract: issue 2, delivered orders can be cancelled

**Goal:** Delivered orders cannot be cancelled (issue #2).

**Context:** AGENTS.md (order state machine), app/modules/orders/service.py (cancel_order), tests/unit/test_orders.py. The report points at routes.py, but the cancel rules live in the service.

**In scope:** app/modules/orders/service.py, tests/unit/test_orders.py, tests/integration/test_orders.py

**Out of scope:** app/modules/orders/routes.py, app/modules/payment/, alembic/, .github/, pyproject.toml, any new dependency

**Acceptance:**
- a new unit test fails on the current code and passes after the fix
- cancelling a DELIVERED order is rejected: the order stays DELIVERED and its invoice is not cancelled
- POST /orders/{id}/cancel on a delivered order returns 400
- `python -m pytest tests/unit -q` passes and no existing assertion is changed

**Stop and ask a human if:** the fix needs a schema change, a change in the payment module, or a change to an existing test

**Reviewer:** your partner (not the requester)
