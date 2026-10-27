# Team design for the capstone (issue 9)
**Pattern:** planner-executor with two workers. **Why:** the task is ambiguous (two modules, a schema, a migration), so a plan comes first; the two implementers touch different modules, so they can work in parallel on separate worktrees.

| Role | Owns paths | Tools | Input | Output | Stop rule |
| --- | --- | --- | --- | --- | --- |
| planner | docs/agent-state/ | read, search, edit (plan only) | the issue | plan + handoff | hop_count >= 3 |
| tester | tests/ | read, edit, search, execute | acceptance criteria | failing tests, then a verification report | never edits an existing assertion |
| implementer-orders | app/modules/orders/ | read, edit, search, execute | plan + interface | orders code, unit tests green | needs a file outside its path: stop and hand back |
| implementer-payment | app/modules/payment/ | read, edit, search, execute | plan + interface | payment code | may call orders interfaces, never edit orders |
| migrator (human or agent) | alembic/versions/ | read, edit | schema change list | one migration | always needs code-owner review |

**Review checklist:** loops (planner <-> implementer): hop limit. Single point of failure: the planner, so the human approves the plan. Files nobody owns: README.md, pyproject.toml (nobody edits; protected by CODEOWNERS). Files two roles own: none.
