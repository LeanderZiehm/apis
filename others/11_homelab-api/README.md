# Minimal Event / Timer / Measurement API  

A tiny FastAPI service that stores **events**, **timers**, **measurements**, **JSON blobs**, and **habits** in a PostgreSQL database.  
All data is persisted with SQLAlchemy and exposed through simple REST endpoints plus an auto‑generated Swagger UI.

---  

## Quick Start (Docker)

```bash
# 1. Set required DB environment variables
export POSTGRES_HOST=your_pg_host
export POSTGRES_PORT=5432
export POSTGRES_DB=your_db
export POSTGRES_USER=your_user
export POSTGRES_PASSWORD=your_password

# 2. Build & run the container
docker compose up --build
```

The API will be reachable at **http://localhost:8802** and the Swagger UI at **http://localhost:8802/docs**.

---  

## Local Development (without Docker)

```bash
# Clone the repo
git clone <repo_url>
cd <repo_dir>

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set the same DB env vars as above
export POSTGRES_HOST=...
export POSTGRES_PORT=...
export POSTGRES_DB=...
export POSTGRES_USER=...
export POSTGRES_PASSWORD=...

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8802
```

---  

## API Overview  

| Resource | Methods | Description |
|----------|---------|-------------|
| **/events** | `POST /events` – create<br>`GET /events` – list | Simple text events. |
| **/timers** | `POST /timers` – create<br>`GET /timers` – list | Timer entries with `START` / `END` actions. |
| **/measurements** | `POST /measurements` – create<br>`GET /measurements` – list | Numeric measurements (`value`). |
| **/json** | `POST /json` – create<br>`GET /json` – list | Arbitrary JSON payloads (`body`). |
| **/habits** | `POST /habits` – create<br>`GET /habits` – list | Habit records with a `when` enum (`NOW`, `TODAY`, `YESTERDAY`, `OTHER`). |

### Common query parameters (GET)

- `limit` (default = 100) – max records returned.  
- Resource‑specific filters (e.g., `text`, `action`, `type`, `when`).  

### Example: Create an event

```bash
curl -X POST http://localhost:8802/events \
  -H "Content-Type: application/json" \
  -d '{"text": "My first event"}'
```

### Example: List recent timers

```bash
curl http://localhost:8802/timers?limit=10
```

---  

## Configuration  

| Variable | Description |
|----------|-------------|
| `POSTGRES_HOST` | PostgreSQL host address |
| `POSTGRES_PORT` | PostgreSQL port (default 5432) |
| `POSTGRES_DB`   | Database name |
| `POSTGRES_USER` | DB user |
| `POSTGRES_PASSWORD` | DB password |

These are read at startup to build the SQLAlchemy connection string.  

---  

## Project Structure  

```
├── Dockerfile          # Build image (python:3.11‑slim)
├── docker-compose.yml  # One‑service definition (app)
├── main.py             # FastAPI app, models, schemas, routes
├── requirements.txt    # Python dependencies
└── README.md           # <‑‑ you are here
```

---  

## License  

MIT – feel free to tweak, extend, or embed in your own projects.  
