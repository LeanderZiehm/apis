local:
	[ ! -d "venv" ] && python -m venv venv && venv/bin/pip install -r requirements.txt; set -a && . ./.env && set +a && venv/bin/uvicorn main:app --port 8809

run:
	uvicorn main:app --port 8809

uv_run:
	set -a && . ./.env && set +a && uv run uvicorn main:app --port 8809

postgres:
	podman run --replace --name pg18 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5432:5432 -v pg18data:/var/lib/postgresql -d docker.io/library/postgres:18

setup_db:
	. ./.env && echo $$DATABASE_URL && psql $$DATABASE_URL ./sql/setup.sql

0 podman container:
	podman build -t nutrients-api . && podman images nutrients-api && podman run --network=host --env-file .env  -p 8809:8809 nutrients-api
# 	podman build -t nutrients-api . && podman images nutrients-api && podman run --env-file .env  -p 8809:8809 nutrients-api