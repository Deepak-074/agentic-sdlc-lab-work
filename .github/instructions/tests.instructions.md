---
applyTo: "tests/**"
---
- Unit tests call service functions with MagicMock repositories (see tests/unit/test_orders.py). No DB, no HTTP.
- One behaviour per test. Name tests test_<function>_<situation>.
- A new bug fix starts with a test that fails on the current code.
- Never weaken or delete an existing assertion to make a test pass. Stop and ask instead.
