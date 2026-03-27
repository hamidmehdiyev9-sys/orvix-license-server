# Orvix License Server

FastAPI service: **7-day trial**, **license keys**, **JWT session ping**, **web admin panel**.

## Local run (SQLite)

```bash
cd license-server
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set JWT_SECRET=dev-secret-change-in-production-min-32-chars
set ADMIN_PASSWORD=your-admin-password
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Same app, if you prefer the legacy filename:
#   uvicorn server:app --reload --host 127.0.0.1 --port 8000
#   python server.py
```

- Health: http://127.0.0.1:8000/health  
- Admin: http://127.0.0.1:8000/admin/login (password = `ADMIN_PASSWORD`)  
- API: `POST /api/v1/device/register`, `/trial/start`, `/license/activate`, `/session/ping`

## Render.com (production)

1. Create a **Web Service**, connect this folder or GitHub repo (root can be `license-server/` or use subdirectory in Render settings).
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
   (or `uvicorn server:app --host 0.0.0.0 --port $PORT` — see `server.py`)
4. Add **PostgreSQL** (free tier) and attach — Render injects `DATABASE_URL`.
5. **Environment variables** (important):

| Variable | Example |
|----------|---------|
| `JWT_SECRET` | Long random string (32+ chars) |
| `ADMIN_PASSWORD` | Strong password for `/admin` |
| `TRIAL_DAYS` | `7` |
| `DATABASE_URL` | Auto from Postgres addon |

6. Deploy. Copy the public **HTTPS URL** (e.g. `https://xxx.onrender.com`).

## Orvix desktop client

On the PC where Orvix runs:

```bat
set ORVIX_LICENSE_SERVER=https://YOUR-SERVICE.onrender.com
```

Development (skip license):

```bat
set ORVIX_LICENSE_SKIP=1
```

Force license server in dev (fail if URL missing):

```bat
set ORVIX_LICENSE_STRICT=1
set ORVIX_LICENSE_SERVER=https://...
```

## GitHub

Push the `license-server` folder (or whole monorepo) to a repository. Render can deploy from GitHub on each push.

**Do not commit** `.env` with real secrets — use Render Environment only.
