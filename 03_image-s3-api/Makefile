all:
	[ ! -d "venv" ] && python -m venv venv && venv/bin/pip install -r requirements.txt; set -a && source ./.env && set +a && venv/bin/uvicorn main:app --reload


run:
	uvicorn main:app --port 8803