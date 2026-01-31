dev:
	cd infra && docker compose up -d --build

down:
	cd infra && docker compose down

test:
	pip install -r requirements-dev.txt
	pytest -q
