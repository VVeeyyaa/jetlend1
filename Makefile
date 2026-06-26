.PHONY: build up down logs migrate test test-ci

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrations:
	docker compose exec web python manage.py makemigrations

migrate:
	docker compose exec web python manage.py migrate

test:
	docker compose exec web pytest --reuse-db -x -q

test-ci:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from web
	docker compose -f docker-compose.test.yml down -v
