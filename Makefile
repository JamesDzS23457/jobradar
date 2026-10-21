.PHONY: install backend frontend dev test lint extension-check seed reset

install:
	cd backend && uv sync --extra dev
	cd frontend && npm install

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Ejecuta 'make backend' y 'make frontend' en dos terminales."

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run build
	$(MAKE) extension-check

extension-check:
	cd extension && for file in *.js; do node --check "$$file"; done
	python3 -m json.tool extension/manifest.json >/dev/null

seed:
	curl -s -X POST http://localhost:8000/api/demo/seed | python3 -m json.tool

reset:
	curl -s -X POST http://localhost:8000/api/demo/reset | python3 -m json.tool
