local:
	[ ! -d "venv" ] && python -m venv venv && venv/bin/pip install -r requirements.txt; set -a && . ./.env && set +a && venv/bin/uvicorn main:app --reload

run:
	uvicorn main:app --port 8803


0 podman container:
	podman build -t homelab-api . && podman images homelab-api && podman run --env-file .env  -p 8811:8811 homelab-api