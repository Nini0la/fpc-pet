backend-install:
	cd backend && uv sync --extra dev
backend-test:
	cd backend && uv run pytest -q
backend-check:
	cd backend && uv run ruff check app tests && uv run mypy app
frontend-install:
	cd frontend && npm ci
frontend-check:
	cd frontend && npm test && npm audit --audit-level=high && npm run lint && npm run typecheck && npm run build
check: backend-test backend-check frontend-check
