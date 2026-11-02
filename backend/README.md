# ITPC ERP Flask API

## Setup

1. Create a PostgreSQL database named `itpc_erp`.
2. Copy `.env.example` to `.env` and update `DATABASE_URL` and `SECRET_KEY`.
3. Create a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

4. Initialize the database schema with migrations:

```powershell
flask --app backend.app db init
flask --app backend.app db migrate -m "initial schema"
flask --app backend.app db upgrade
```

Run `db init` only once. For later model changes, run `db migrate` and
`db upgrade`. For a new local demo database without migrations,
`AUTO_CREATE_SCHEMA=1` is enabled by default. Set `AUTO_CREATE_SCHEMA=0` when
using migrations or any production database.

5. Start the API from the repository root:

```powershell
python backend\app.py
```

The API runs at `http://127.0.0.1:5000`. The first start creates the tables and
seeds `admin` and `member` accounts. Set `ADMIN_PASSWORD` and `MEMBER_PASSWORD`
before the first start to avoid the development defaults.

## Endpoints

- `GET /api/health`
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/users` (administrator)
- `GET/POST/PATCH /api/inventory`
- `GET/PUT /api/officers`
- `GET/POST /api/events`
- `GET /api/archives`
- `GET /api/audit-logs` (authenticated users)
- `GET /api/reports/summary`

The browser session is an HTTP-only Flask session cookie. All write endpoints
require an administrator role, and archive operations plus changes are recorded
in PostgreSQL.

The browser migration currently synchronizes inventory, events, and archives
through the protected `PUT /api/inventory/sync`, `PUT /api/events/sync`,
`PUT /api/officers/sync`, and `PUT /api/archives/sync` endpoints.
