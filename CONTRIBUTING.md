# Contributing

Read [README](README.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [AGENTS.md](AGENTS.md) before changing runtime behavior.

## Local development

1. Run `scripts/setup.sh` to install pinned dependencies and build the UI.
2. Start `scripts/start.sh` and, for frontend development, `npm run dev` inside `frontend`.
3. Keep model and source providers behind their existing interfaces. Do not introduce paid dependencies or cloud inference.
4. Add tests for meaningful changes to identity handling, source grounding, network boundaries, budgets, cancellation or persistence.
5. Run `.venv/bin/ruff check backend`, `.venv/bin/pytest -q`, `npm run build --prefix frontend` and affected browser tests.
6. Update the changelog and document material limitations. Do not commit data, model weights or private investigations.

Formatting: `.venv/bin/ruff format backend` and `frontend/node_modules/.bin/prettier --write frontend/src`.

Bug reports should include Locus version, OS, model identifier and mode, expected behavior and a minimal non-sensitive reproduction. Remove personal research data from logs before sharing.

Dependency updates require refreshed lockfiles and passing tests. Schema changes require explicit migration, recovery and backup tests. A change that improves the number of retrieved pages but increases mistaken identity is not automatically an improvement.
