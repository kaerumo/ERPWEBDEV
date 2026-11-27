# ITPC ERP

ERP for the DLSU-D Information Technology Program Council. The existing HTML,
CSS, and JavaScript interface is served by Django. Django handles login,
session security, validation, and role enforcement; PostgreSQL stores the
shared inventory, officers, events, dashboard activity, and change log.

## Features

- Inventory management, quantity and low-stock tracking, search, filters, and CSV export
- Officer and event management, calendar, dashboard, and printable reports
- Django-backed admin/member accounts: members can view data; staff users can manage it
- PostgreSQL-backed records shared by all authenticated users
- Admin-only JSON backup and restore, and a change log
- Responsive interface, theme toggle, and existing dialogs and notifications

## Run locally with PostgreSQL

Docker Compose starts PostgreSQL and the Django development server:

1. Copy the environment template and edit `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` with private values
   before exposing the app beyond your computer.

2. Build and start the services:

   ```powershell
   docker compose up --build
   ```

3. In a second terminal, create the first administrator:

   ```powershell
   docker compose exec web python manage.py createsuperuser
   ```

4. Open <http://localhost:8000/> and sign in. Use Django Admin at
   <http://localhost:8000/admin/> to create member accounts. Leave **Staff
   status** unchecked for members; staff users have administrator access.

The Compose setup is for local development, not production. For production,
use a production WSGI server, HTTPS, a strong secret key, restricted
`DJANGO_ALLOWED_HOSTS`, and managed PostgreSQL backups.

## Run without Docker

Python 3.10+ is required. Install dependencies with
`python -m pip install -r requirements.txt`. Without `DATABASE_URL`, Django uses a local SQLite database
for development. To use PostgreSQL, set `DATABASE_URL` to a PostgreSQL
connection URL in the shell, then run:

```powershell
$env:DJANGO_DEBUG = "True"
$env:DJANGO_SECRET_KEY = "local-development-only-change-this"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run the backend tests with `python manage.py test`.

## Existing browser data

Data from the former browser-only version is not copied automatically. Before
switching versions, download a JSON backup from the old app. After signing in
to the Django version as an administrator, use **Restore from backup** to
import it into PostgreSQL.

## Security notes

- Django stores password hashes and uses server-side sessions and CSRF checks.
- Role checks and write validation run on the server; hiding admin controls in
  the browser is not the security boundary.
- The change log is stored in PostgreSQL. As with any audit trail, restrict
  database and Django Admin access to trusted administrators.
- Do not commit `.env` or use the example secret/password values in a deployed
  environment.
