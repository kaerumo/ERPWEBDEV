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
seeds `admin` and `member` accounts plus the sample inventory, borrowable
equipment, officers, and events. Set `ADMIN_PASSWORD` and `MEMBER_PASSWORD`
before the first start to avoid the development defaults. Existing records are
preserved; missing sample equipment inventory rows are added without replacing
user data.

## Endpoints

- `GET /api/health`
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/users` (administrator)
- `POST/PATCH /api/users` (administrator user administration)
- `GET/POST/PATCH /api/inventory`
- `GET/POST /api/equipment`; `GET/POST/PATCH /api/borrowing-requests` and
  `POST /api/borrowing-requests/<id>/return`; `/overdue` reports outstanding
  overdue equipment. Borrowing requests create approval history automatically.
- `GET/POST /api/approvals`, `PATCH /api/approvals/<id>` (administrator review)
- `GET /api/notifications`, `PATCH /api/notifications/<id>/read`
- `GET/POST/PATCH /api/suppliers`
- `GET/POST /api/purchases`, `/api/expenses`, and `/api/budgets`
- `GET/PUT /api/officers`
- `GET/POST /api/events`
- `GET /api/archives`
- `GET /api/audit-logs` (authenticated users)
- `GET /api/reports/summary`
- `GET /api/places/search?q=...`
- `GET/POST /api/equipment`
- `GET/POST/PATCH /api/borrowing-requests`
- `GET/PATCH /api/approvals`
- `GET/PATCH /api/notifications`
- `GET/POST/PATCH /api/suppliers`
- `GET/POST /api/purchases`, `/api/expenses`, and `/api/budgets`

The browser session is an HTTP-only Flask session cookie. All write endpoints
require an administrator role, and archive operations plus changes are recorded
in PostgreSQL.

The Operations page uses PostgreSQL workflows for equipment borrowing and
returns, approval review, notifications, suppliers, purchases, expenses, and
budgets. The first local backend start also seeds three sample equipment
records when the equipment table is empty. Those assets are also added to
Inventory when missing, so Projector, DSLR Camera, and Wireless Microphone
appear in both the stock list and the equipment register.

The enterprise foundation uses PostgreSQL tables for equipment lending and
returns (including damage and overdue state), approval history, notifications,
suppliers, purchases, expenses, budgets, and user administration. Apply the
`2f4d8a1b7c9e_enterprise_foundation` migration after the existing initial
revision:

```powershell
flask --app backend.app db upgrade
```

Members may submit and return their own equipment requests; administrator-only
endpoints create/update master data and review approvals. All state changes
write an `audit_logs` record and relevant approval/borrowing changes notify
the affected user.

Borrowing requests validate that the return date is on or after the borrowing
date. The Operations approval view displays the equipment, purpose, borrowing
date, return date, and requester details for each approval.

The browser migration currently synchronizes inventory, events, and archives
through the protected `PUT /api/inventory/sync`, `PUT /api/events/sync`,
`PUT /api/officers/sync`, and `PUT /api/archives/sync` endpoints.

Event place search uses a configurable geocoding provider. The local default is
OpenStreetMap Nominatim and results are restricted to the Philippines.
Configure `PLACE_SEARCH_URL` and a descriptive `PLACE_SEARCH_USER_AGENT` for
your deployment, or replace this adapter with Google Places/Mapbox when the
organization chooses a paid provider and API terms. Never put a provider
secret in frontend JavaScript.

If the database already existed before the location fields were added, create a
Flask-Migrate revision and apply it before starting the API:

```powershell
flask --app backend.app db migrate -m "add event location metadata"
flask --app backend.app db upgrade
```
