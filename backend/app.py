import os
from datetime import date, datetime, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="member")
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    specification = db.Column(db.String(255), nullable=False, default="")
    category = db.Column(db.String(40), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False, default="")
    event_type = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Officer(db.Model):
    __tablename__ = "officers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    position = db.Column(db.String(40), nullable=False)
    committee = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")


class Archive(db.Model):
    __tablename__ = "archives"

    id = db.Column(db.Integer, primary_key=True)
    record_type = db.Column(db.String(30), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    record = db.Column(db.JSON, nullable=False)
    archived_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module = db.Column(db.String(40), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    target = db.Column(db.String(160), nullable=False)
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def create_app():
    app = Flask(__name__)
    secret_key = os.environ.get("SECRET_KEY")
    if os.environ.get("FLASK_ENV") == "production" and not secret_key:
        raise RuntimeError("SECRET_KEY must be configured in production.")
    app.config["SECRET_KEY"] = secret_key or "development-only-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/itpc_erp",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    db.init_app(app)
    migrate.init_app(app, db)

    origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]
    CORS(
        app,
        supports_credentials=True,
        origins=origins or ["http://localhost:5500", "http://127.0.0.1:5500"],
    )

    with app.app_context():
        if os.environ.get("AUTO_CREATE_SCHEMA", "1") == "1":
            db.create_all()
        seed_users()

    register_routes(app)
    return app


def seed_users():
    if User.query.count():
        return
    db.session.add_all(
        [
            User(
                username="admin",
                display_name="Admin",
                role="admin",
                password_hash=generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123")),
            ),
            User(
                username="member",
                display_name="Member",
                role="member",
                password_hash=generate_password_hash(os.environ.get("MEMBER_PASSWORD", "member123")),
            ),
        ]
    )
    db.session.commit()


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify(error="Authentication required."), 401
        return handler(*args, **kwargs)

    return wrapped


def admin_required(handler):
    @wraps(handler)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user().role != "admin":
            return jsonify(error="Administrator permission required."), 403
        return handler(*args, **kwargs)

    return wrapped


def parse_json():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def item_json(item):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "specification": item.specification,
        "category": item.category,
        "quantity": item.quantity,
    }


def event_json(event):
    return {
        "id": event.id,
        "title": event.title,
        "date": event.date.isoformat(),
        "time": event.time,
        "type": event.event_type,
        "location": event.location,
        "description": event.description,
    }


def officer_json(officer):
    return {
        "id": officer.id,
        "name": officer.name,
        "position": officer.position,
        "committee": officer.committee,
        "status": officer.status,
    }


def log_change(module, action, target, details=None):
    db.session.add(
        AuditLog(
            user_id=current_user().id,
            module=module,
            action=action,
            target=target,
            details=details or {},
        )
    )


def register_routes(app):
    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="itpc-erp-api")

    @app.post("/api/auth/login")
    def login():
        try:
            data = parse_json()
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", ""))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        user = User.query.filter_by(username=username, status="active").first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify(error="Invalid username or password."), 401
        session["user_id"] = user.id
        return jsonify(user={"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role})

    @app.post("/api/auth/logout")
    @login_required
    def logout():
        session.clear()
        return jsonify(message="Logged out.")

    @app.get("/api/auth/me")
    @login_required
    def me():
        user = current_user()
        return jsonify(user={"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role})

    @app.get("/api/users")
    @admin_required
    def users():
        return jsonify(
            users=[
                {"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role, "status": user.status}
                for user in User.query.order_by(User.id).all()
            ]
        )

    @app.get("/api/inventory")
    @login_required
    def inventory():
        query = InventoryItem.query
        search = request.args.get("search", "").strip()
        if search:
            query = query.filter(InventoryItem.name.ilike(f"%{search}%"))
        return jsonify(items=[item_json(item) for item in query.order_by(InventoryItem.name).all()])

    @app.post("/api/inventory")
    @admin_required
    def create_inventory():
        try:
            data = parse_json()
            name = str(data.get("name", "")).strip()
            quantity = data.get("quantity")
            if not name or not isinstance(quantity, int) or quantity < 0:
                raise ValueError("Name and a non-negative whole-number quantity are required.")
            item = InventoryItem(
                name=name,
                description=str(data.get("description", "")).strip(),
                specification=str(data.get("specification", "")).strip(),
                category=str(data.get("category", "")).strip(),
                quantity=quantity,
            )
            db.session.add(item)
            db.session.flush()
            log_change("inventory", "add", name, item_json(item))
            db.session.commit()
            return jsonify(item=item_json(item)), 201
        except ValueError as error:
            db.session.rollback()
            return jsonify(error=str(error)), 400

    @app.patch("/api/inventory/<int:item_id>")
    @admin_required
    def update_inventory(item_id):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            return jsonify(error="Inventory item not found."), 404
        try:
            data = parse_json()
            if "quantity" in data and (not isinstance(data["quantity"], int) or data["quantity"] < 0):
                raise ValueError("Quantity must be a non-negative whole number.")
            before = item_json(item)
            for field in ("name", "description", "specification", "category", "quantity"):
                if field in data:
                    setattr(item, field, data[field])
            log_change("inventory", "edit", item.name, {"before": before, "after": item_json(item)})
            db.session.commit()
            return jsonify(item=item_json(item))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            return jsonify(error=str(error)), 400

    @app.delete("/api/inventory/<int:item_id>")
    @admin_required
    def archive_inventory(item_id):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            return jsonify(error="Inventory item not found."), 404
        archive = Archive(record_type="inventory", record_id=item.id, name=item.name, record=item_json(item), archived_by=current_user().id)
        db.session.add(archive)
        log_change("inventory", "archive", item.name, item_json(item))
        db.session.delete(item)
        db.session.commit()
        return jsonify(message="Inventory item archived.")

    @app.put("/api/inventory/sync")
    @admin_required
    def sync_inventory():
        try:
            data = parse_json()
            items = data.get("items")
            if not isinstance(items, list):
                raise ValueError("items must be a list.")
            incoming_ids = {int(item["id"]) for item in items}
            for item in InventoryItem.query.all():
                if item.id not in incoming_ids:
                    db.session.delete(item)
            for payload in items:
                item = db.session.get(InventoryItem, int(payload["id"]))
                if item is None:
                    item = InventoryItem(id=int(payload["id"]))
                    db.session.add(item)
                item.name = str(payload["name"]).strip()
                item.description = str(payload.get("description", "")).strip()
                item.specification = str(payload.get("specification", "")).strip()
                item.category = str(payload["category"]).strip()
                item.quantity = int(payload["quantity"])
            db.session.commit()
            return jsonify(message="Inventory synchronized.")
        except (KeyError, TypeError, ValueError) as error:
            db.session.rollback()
            return jsonify(error="Invalid inventory payload: " + str(error)), 400

    @app.get("/api/events")
    @login_required
    def events():
        return jsonify(events=[event_json(event) for event in Event.query.order_by(Event.date, Event.time).all()])

    @app.get("/api/officers")
    @login_required
    def officers():
        return jsonify(officers=[officer_json(officer) for officer in Officer.query.order_by(Officer.name).all()])

    @app.put("/api/officers/sync")
    @admin_required
    def sync_officers():
        try:
            data = parse_json()
            officers_payload = data.get("officers")
            if not isinstance(officers_payload, list):
                raise ValueError("officers must be a list.")
            incoming_ids = {int(item["id"]) for item in officers_payload}
            for officer in Officer.query.all():
                if officer.id not in incoming_ids:
                    db.session.delete(officer)
            for payload in officers_payload:
                officer = db.session.get(Officer, int(payload["id"]))
                if officer is None:
                    officer = Officer(id=int(payload["id"]))
                    db.session.add(officer)
                officer.name = str(payload["name"]).strip()
                officer.position = str(payload["position"]).strip()
                officer.committee = str(payload["committee"]).strip()
                officer.status = str(payload["status"]).strip()
            db.session.commit()
            return jsonify(message="Officers synchronized.")
        except (KeyError, TypeError, ValueError) as error:
            db.session.rollback()
            return jsonify(error="Invalid officers payload: " + str(error)), 400

    @app.post("/api/events")
    @admin_required
    def create_event():
        try:
            data = parse_json()
            event_date = date.fromisoformat(str(data.get("date", "")))
            if event_date < date.today():
                raise ValueError("New events must be today or later.")
            title = str(data.get("title", "")).strip()
            location = str(data.get("location", "")).strip()
            if not title or not location:
                raise ValueError("Title and location are required.")
            event = Event(title=title, date=event_date, time=str(data.get("time", "")), event_type=str(data.get("type", "meeting")), location=location, description=str(data.get("description", "")).strip())
            db.session.add(event)
            db.session.flush()
            log_change("events", "add", title, event_json(event))
            db.session.commit()
            return jsonify(event=event_json(event)), 201
        except (ValueError, TypeError) as error:
            db.session.rollback()
            return jsonify(error=str(error)), 400

    @app.patch("/api/events/<int:event_id>")
    @admin_required
    def update_event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify(error="Event not found."), 404
        try:
            data = parse_json()
            next_date = date.fromisoformat(str(data.get("date", event.date.isoformat())))
            if next_date < date.today() and next_date != event.date:
                raise ValueError("Events cannot be rescheduled into the past.")
            before = event_json(event)
            for field in ("title", "time", "location", "description"):
                if field in data:
                    setattr(event, field, str(data[field]).strip())
            if "type" in data:
                event.event_type = str(data["type"]).strip()
            event.date = next_date
            log_change("events", "edit", event.title, {"before": before, "after": event_json(event)})
            db.session.commit()
            return jsonify(event=event_json(event))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            return jsonify(error=str(error)), 400

    @app.delete("/api/events/<int:event_id>")
    @admin_required
    def archive_event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify(error="Event not found."), 404
        record = event_json(event)
        db.session.add(Archive(record_type="events", record_id=event.id, name=event.title, record=record, archived_by=current_user().id))
        log_change("events", "archive", event.title, record)
        db.session.delete(event)
        db.session.commit()
        return jsonify(message="Event archived.")

    @app.put("/api/events/sync")
    @admin_required
    def sync_events():
        try:
            data = parse_json()
            events_payload = data.get("events")
            if not isinstance(events_payload, list):
                raise ValueError("events must be a list.")
            incoming_ids = {int(item["id"]) for item in events_payload}
            for event in Event.query.all():
                if event.id not in incoming_ids:
                    db.session.delete(event)
            for payload in events_payload:
                event = db.session.get(Event, int(payload["id"]))
                if event is None:
                    event = Event(id=int(payload["id"]))
                    db.session.add(event)
                event.title = str(payload["title"]).strip()
                event.date = date.fromisoformat(str(payload["date"]))
                event.time = str(payload.get("time", ""))
                event.event_type = str(payload.get("type", "meeting"))
                event.location = str(payload["location"]).strip()
                event.description = str(payload.get("description", "")).strip()
            db.session.commit()
            return jsonify(message="Events synchronized.")
        except (KeyError, TypeError, ValueError) as error:
            db.session.rollback()
            return jsonify(error="Invalid events payload: " + str(error)), 400

    @app.get("/api/archives")
    @login_required
    def archives():
        return jsonify(
            archives=[
                {"id": entry.id, "type": entry.record_type, "name": entry.name, "record": entry.record, "archivedAt": entry.archived_at.isoformat(), "archivedBy": entry.archived_by}
                for entry in Archive.query.order_by(Archive.archived_at.desc()).all()
            ]
        )

    @app.post("/api/archives/<int:archive_id>/restore")
    @admin_required
    def restore_archive(archive_id):
        entry = db.session.get(Archive, archive_id)
        if not entry:
            return jsonify(error="Archive entry not found."), 404
        record = entry.record
        if entry.record_type == "inventory":
            if db.session.get(InventoryItem, entry.record_id):
                return jsonify(error="The inventory record already exists."), 409
            db.session.add(InventoryItem(id=entry.record_id, name=record["name"], description=record.get("description", ""), specification=record.get("specification", ""), category=record["category"], quantity=record["quantity"]))
        elif entry.record_type == "events":
            if db.session.get(Event, entry.record_id):
                return jsonify(error="The event record already exists."), 409
            db.session.add(Event(id=entry.record_id, title=record["title"], date=date.fromisoformat(record["date"]), time=record.get("time", ""), event_type=record.get("type", "meeting"), location=record["location"], description=record.get("description", "")))
        else:
            return jsonify(error="This archive type cannot be restored yet."), 400
        log_change(entry.record_type, "restore", entry.name, record)
        db.session.delete(entry)
        db.session.commit()
        return jsonify(message="Archive restored.")

    @app.delete("/api/archives/<int:archive_id>")
    @admin_required
    def purge_archive(archive_id):
        entry = db.session.get(Archive, archive_id)
        if not entry:
            return jsonify(error="Archive entry not found."), 404
        log_change(entry.record_type, "purge", entry.name, entry.record)
        db.session.delete(entry)
        db.session.commit()
        return jsonify(message="Archive deleted permanently.")

    @app.put("/api/archives/sync")
    @admin_required
    def sync_archives():
        try:
            data = parse_json()
            archives_payload = data.get("archives")
            if not isinstance(archives_payload, list):
                raise ValueError("archives must be a list.")
            Archive.query.delete()
            for payload in archives_payload:
                db.session.add(
                    Archive(
                        id=int(payload["id"]),
                        record_type=str(payload["type"]),
                        record_id=int(payload["record"]["id"]),
                        name=str(payload["name"]),
                        record=payload["record"],
                        archived_by=current_user().id,
                        archived_at=datetime.fromisoformat(payload["archivedAt"]),
                    )
                )
            db.session.commit()
            return jsonify(message="Archives synchronized.")
        except (KeyError, TypeError, ValueError) as error:
            db.session.rollback()
            return jsonify(error="Invalid archives payload: " + str(error)), 400

    @app.get("/api/audit-logs")
    @login_required
    def audit_logs():
        return jsonify(
            logs=[
                {
                    "id": log.id,
                    "module": log.module,
                    "action": log.action,
                    "target": log.target,
                    "details": log.details,
                    "user": db.session.get(User, log.user_id).display_name,
                    "role": db.session.get(User, log.user_id).role,
                    "time": log.created_at.isoformat(),
                }
                for log in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(1000).all()
            ]
        )

    @app.get("/api/reports/summary")
    @login_required
    def report_summary():
        items = InventoryItem.query.all()
        officers_list = Officer.query.all()
        upcoming_events = Event.query.filter(Event.date >= date.today()).order_by(Event.date, Event.time).limit(10).all()
        return jsonify(
            summary={
                "inventoryCount": len(items),
                "totalUnits": sum(item.quantity for item in items),
                "lowStockCount": sum(item.quantity <= 5 for item in items),
                "activeOfficerCount": sum(officer.status == "active" for officer in officers_list),
                "upcomingEvents": [event_json(event) for event in upcoming_events],
            }
        )

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error", exc_info=error)
        return jsonify(error="The server could not complete the request."), 500


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
