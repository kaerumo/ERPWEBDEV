import os
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
from datetime import date, datetime, timedelta, timezone
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
    address = db.Column(db.String(255), nullable=False, default="")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    map_url = db.Column(db.String(500), nullable=False, default="")
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


class Equipment(db.Model):
    __tablename__ = "equipment"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    asset_tag = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(30), nullable=False, default="available")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class BorrowingRequest(db.Model):
    __tablename__ = "borrowing_requests"
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    requested_from = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    returned_at = db.Column(db.DateTime(timezone=True))
    condition = db.Column(db.String(30), nullable=False, default="good")
    damage_notes = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(30), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ApprovalRequest(db.Model):
    __tablename__ = "approval_requests"
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(40), nullable=False)
    reference_id = db.Column(db.Integer, nullable=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    comments = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime(timezone=True))


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    contact_name = db.Column(db.String(120), nullable=False, default="")
    email = db.Column(db.String(160), nullable=False, default="")
    phone = db.Column(db.String(50), nullable=False, default="")
    address = db.Column(db.String(255), nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PurchaseRecord(db.Model):
    __tablename__ = "purchase_records"
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="recorded")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="submitted")
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Budget(db.Model):
    __tablename__ = "budgets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
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
        seed_demo_data()

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


def seed_demo_data():
    has_core_data = InventoryItem.query.count() or Officer.query.count() or Event.query.count()
    if not Equipment.query.count():
        db.session.add_all(
            [
                Equipment(name="Projector", asset_tag="AV-001", description="Portable projector for presentations."),
                Equipment(name="DSLR Camera", asset_tag="AV-002", description="Camera for event documentation."),
                Equipment(name="Wireless Microphone", asset_tag="AV-003", description="Microphone set for programs and assemblies."),
            ]
        )
    equipment_inventory = [
        ("Projector", "Portable projector for presentations.", "HD; HDMI input", 1),
        ("DSLR Camera", "Camera for event documentation.", "Interchangeable lens; AV-002", 1),
        ("Wireless Microphone", "Microphone set for programs and assemblies.", "Two handheld microphones; AV-003", 2),
    ]
    next_inventory_id = max((item.id for item in InventoryItem.query.all()), default=0) + 1
    for name, description, specification, quantity in equipment_inventory:
        if not InventoryItem.query.filter_by(name=name).first():
            db.session.add(
                InventoryItem(
                    id=next_inventory_id,
                    name=name,
                    category="event-materials",
                    quantity=quantity,
                    description=description,
                    specification=specification,
                )
            )
            next_inventory_id += 1
    if has_core_data:
        db.session.commit()
        return

    today = date.today()
    db.session.add_all(
        [
            InventoryItem(
                name="ITPC Org T-Shirts (S-XL)",
                category="merchandise",
                quantity=35,
                description="Official organization shirt for ITPC members.",
                specification="Sizes S to XL; cotton blend",
            ),
            InventoryItem(
                name="Tarpaulins (event banners)",
                category="event-materials",
                quantity=2,
                description="Reusable banners for council programs and assemblies.",
                specification="3 ft x 6 ft; vinyl",
            ),
            InventoryItem(
                name="Certificate holders",
                category="office-supplies",
                quantity=15,
                description="Folder-style holders for certificates and awards.",
                specification="A4; red cardstock",
            ),
            InventoryItem(
                name="ITPC lanyards",
                category="merchandise",
                quantity=48,
                description="Branded lanyards for officers and event attendees.",
                specification="20 mm polyester; printed",
            ),
            InventoryItem(
                name="Extension cords",
                category="event-materials",
                quantity=4,
                description="Power extension cords for event equipment.",
                specification="10 m; 4-outlet surge protected",
            ),
            InventoryItem(
                name="Bond paper (reams)",
                category="office-supplies",
                quantity=12,
                description="White paper for forms, reports and printed materials.",
                specification="A4; 80 gsm; 500 sheets per ream",
            ),
        ]
    )
    db.session.add_all(
        [
            Officer(id=1, name="Sample President", position="president", committee="Executive", status="active"),
            Officer(id=2, name="Sample Officer A", position="committee-head", committee="Events", status="active"),
            Officer(id=3, name="Sample Officer B", position="member", committee="Logistics", status="inactive"),
            Officer(id=4, name="Sample Officer C", position="member", committee="Events", status="active"),
            Officer(id=5, name="Sample Officer D", position="committee-head", committee="Logistics", status="active"),
        ]
    )
    db.session.add_all(
        [
            Event(id=1, title="General Assembly", date=today + timedelta(days=2), time="13:00", event_type="meeting", location="Main Auditorium", description="Semester kickoff with all officers and members."),
            Event(id=2, title="Web Dev Workshop", date=today + timedelta(days=5), time="09:00", event_type="workshop", location="Computer Lab 3", description="Hands-on HTML, CSS and JavaScript session."),
            Event(id=3, title="Officers Meeting", date=today + timedelta(days=9), time="16:30", event_type="meeting", location="ITPC Office", description="Budget and logistics planning."),
            Event(id=4, title="ITPC Night", date=today + timedelta(days=16), time="18:00", event_type="social", location="University Grounds", description="Annual org night with games and performances."),
            Event(id=5, title="Tech Talk: Careers in IT", date=today + timedelta(days=23), time="14:00", event_type="seminar", location="Lecture Hall 2", description="Industry guests discuss careers in technology."),
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
    result = {
        "id": event.id,
        "title": event.title,
        "date": event.date.isoformat(),
        "time": event.time,
        "type": event.event_type,
        "location": event.location,
        "description": event.description,
    }
    if hasattr(event, "address"):
        result.update(
            {
                "address": event.address,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "mapUrl": event.map_url,
            }
        )
    return result


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


def _date(value, field):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD).")


def _amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("amount must be a non-negative number.")
    if amount < 0:
        raise ValueError("amount must be a non-negative number.")
    return amount


def _json_value(value):
    return float(value) if value is not None else None


def _equipment_json(item):
    return {"id": item.id, "name": item.name, "assetTag": item.asset_tag, "description": item.description, "status": item.status}


def _borrowing_json(item):
    equipment = db.session.get(Equipment, item.equipment_id)
    return {"id": item.id, "equipmentId": item.equipment_id, "equipment": equipment.name if equipment else None,
            "borrowerId": item.borrower_id, "purpose": item.purpose, "requestedFrom": item.requested_from.isoformat(),
            "dueDate": item.due_date.isoformat(), "returnedAt": item.returned_at.isoformat() if item.returned_at else None,
            "condition": item.condition, "damageNotes": item.damage_notes, "status": item.status, "overdue": item.status not in ("returned", "rejected") and item.due_date < date.today()}


def _approval_json(item):
    return {"id": item.id, "type": item.request_type, "referenceId": item.reference_id, "requestedBy": item.requested_by,
            "reviewedBy": item.reviewed_by, "status": item.status, "comments": item.comments,
            "createdAt": item.created_at.isoformat(), "reviewedAt": item.reviewed_at.isoformat() if item.reviewed_at else None}


def _supplier_json(item):
    return {"id": item.id, "name": item.name, "contactName": item.contact_name, "email": item.email, "phone": item.phone, "address": item.address, "status": item.status}


def _financial_json(item, kind):
    result = {"id": item.id, "amount": _json_value(item.amount), "status": item.status, "createdAt": item.created_at.isoformat()}
    if kind == "purchase":
        result.update({"supplierId": item.supplier_id, "description": item.description, "purchaseDate": item.purchase_date.isoformat()})
    elif kind == "expense":
        result.update({"category": item.category, "description": item.description, "expenseDate": item.expense_date.isoformat()})
    else:
        result.update({"name": item.name, "category": item.category, "periodStart": item.period_start.isoformat(), "periodEnd": item.period_end.isoformat()})
    return result


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

    @app.post("/api/users")
    @admin_required
    def create_user():
        try:
            data = parse_json()
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", ""))
            display_name = str(data.get("displayName", "")).strip()
            role = str(data.get("role", "member")).strip()
            if not username or len(password) < 8 or not display_name or role not in ("admin", "member"):
                raise ValueError("username, displayName, a password of at least 8 characters, and a valid role are required.")
            if User.query.filter_by(username=username).first():
                return jsonify(error="Username already exists."), 409
            user = User(username=username, display_name=display_name, role=role, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.flush()
            log_change("users", "add", username, {"role": role}); db.session.commit()
            return jsonify(user={"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role, "status": user.status}), 201
        except ValueError as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.patch("/api/users/<int:user_id>")
    @admin_required
    def update_user(user_id):
        user = db.session.get(User, user_id)
        if not user: return jsonify(error="User not found."), 404
        try:
            data = parse_json()
            if "role" in data and data["role"] not in ("admin", "member"): raise ValueError("Invalid role.")
            if "status" in data and data["status"] not in ("active", "disabled"): raise ValueError("Invalid status.")
            for key, field in (("displayName", "display_name"), ("role", "role"), ("status", "status")):
                if key in data: setattr(user, field, str(data[key]).strip())
            if "password" in data:
                if len(str(data["password"])) < 8: raise ValueError("Password must be at least 8 characters.")
                user.password_hash = generate_password_hash(str(data["password"]))
            log_change("users", "edit", user.username, data); db.session.commit()
            return jsonify(message="User updated.")
        except (ValueError, TypeError) as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.get("/api/equipment")
    @login_required
    def equipment():
        return jsonify(equipment=[_equipment_json(item) for item in Equipment.query.order_by(Equipment.name).all()])

    @app.post("/api/equipment")
    @admin_required
    def create_equipment():
        try:
            data = parse_json(); name = str(data.get("name", "")).strip(); tag = str(data.get("assetTag", "")).strip()
            if not name or not tag: raise ValueError("name and assetTag are required.")
            item = Equipment(name=name, asset_tag=tag, description=str(data.get("description", "")).strip())
            db.session.add(item); db.session.flush(); log_change("equipment", "add", name, _equipment_json(item)); db.session.commit()
            return jsonify(equipment=_equipment_json(item)), 201
        except ValueError as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.post("/api/borrowing-requests")
    @login_required
    def create_borrowing():
        try:
            data = parse_json(); equipment_id = int(data.get("equipmentId")); start = _date(data.get("requestedFrom"), "requestedFrom"); due = _date(data.get("dueDate"), "dueDate")
            item = db.session.get(Equipment, equipment_id)
            if not item or item.status != "available": raise ValueError("Equipment is not available.")
            if due < start: raise ValueError("dueDate must not precede requestedFrom.")
            req = BorrowingRequest(equipment_id=equipment_id, borrower_id=current_user().id, purpose=str(data.get("purpose", "")).strip(), requested_from=start, due_date=due)
            if not req.purpose: raise ValueError("purpose is required.")
            db.session.add(req); db.session.flush(); db.session.add(ApprovalRequest(request_type="equipment_borrowing", reference_id=req.id, requested_by=current_user().id))
            log_change("borrowing", "request", str(req.id), _borrowing_json(req)); db.session.commit()
            return jsonify(request=_borrowing_json(req)), 201
        except (ValueError, TypeError) as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.get("/api/borrowing-requests")
    @login_required
    def borrowings():
        query = BorrowingRequest.query if current_user().role == "admin" else BorrowingRequest.query.filter_by(borrower_id=current_user().id)
        return jsonify(requests=[_borrowing_json(item) for item in query.order_by(BorrowingRequest.created_at.desc()).all()])

    @app.get("/api/borrowing-requests/overdue")
    @login_required
    def overdue_borrowings():
        query = BorrowingRequest.query.filter(BorrowingRequest.due_date < date.today(), BorrowingRequest.status.notin_(("returned", "rejected")))
        if current_user().role != "admin": query = query.filter_by(borrower_id=current_user().id)
        return jsonify(requests=[_borrowing_json(item) for item in query.order_by(BorrowingRequest.due_date).all()])

    @app.patch("/api/borrowing-requests/<int:request_id>")
    @admin_required
    def update_borrowing(request_id):
        item = db.session.get(BorrowingRequest, request_id)
        if not item: return jsonify(error="Borrowing request not found."), 404
        try:
            data = parse_json(); status = str(data.get("status", item.status))
            if status not in ("approved", "rejected", "returned", "damaged", "overdue"): raise ValueError("Invalid borrowing status.")
            item.status = status
            if status in ("returned", "damaged"): item.returned_at = datetime.now(timezone.utc)
            item.condition = str(data.get("condition", item.condition)); item.damage_notes = str(data.get("damageNotes", item.damage_notes)).strip()
            if status in ("approved", "overdue", "damaged"): db.session.get(Equipment, item.equipment_id).status = "borrowed" if status == "approved" else status
            db.session.add(Notification(user_id=item.borrower_id, title="Borrowing request updated", message=f"Request #{item.id} is {status}."))
            log_change("borrowing", "status", str(item.id), {"status": status}); db.session.commit()
            return jsonify(request=_borrowing_json(item))
        except (ValueError, TypeError) as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.post("/api/borrowing-requests/<int:request_id>/return")
    @login_required
    def return_borrowing(request_id):
        item = db.session.get(BorrowingRequest, request_id)
        if not item or (current_user().role != "admin" and item.borrower_id != current_user().id): return jsonify(error="Borrowing request not found."), 404
        data = request.get_json(silent=True) or {}; item.status = "damaged" if data.get("condition") == "damaged" else "returned"; item.condition = str(data.get("condition", "good")); item.damage_notes = str(data.get("damageNotes", "")).strip(); item.returned_at = datetime.now(timezone.utc)
        equipment_item = db.session.get(Equipment, item.equipment_id); equipment_item.status = "damaged" if item.status == "damaged" else "available"
        log_change("borrowing", "return", str(item.id), _borrowing_json(item)); db.session.commit()
        return jsonify(request=_borrowing_json(item))

    @app.get("/api/approvals")
    @login_required
    def approvals():
        query = ApprovalRequest.query if current_user().role == "admin" else ApprovalRequest.query.filter_by(requested_by=current_user().id)
        return jsonify(approvals=[_approval_json(item) for item in query.order_by(ApprovalRequest.created_at.desc()).all()])

    @app.post("/api/approvals")
    @login_required
    def create_approval():
        try:
            data = parse_json()
            request_type = str(data.get("type", "")).strip()
            if not request_type: raise ValueError("type is required.")
            item = ApprovalRequest(request_type=request_type, reference_id=data.get("referenceId"), requested_by=current_user().id, comments=str(data.get("comments", "")).strip())
            db.session.add(item); db.session.flush(); log_change("approvals", "request", str(item.id), _approval_json(item)); db.session.commit()
            return jsonify(approval=_approval_json(item)), 201
        except (ValueError, TypeError) as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.patch("/api/approvals/<int:approval_id>")
    @admin_required
    def review_approval(approval_id):
        item = db.session.get(ApprovalRequest, approval_id)
        if not item: return jsonify(error="Approval request not found."), 404
        data = request.get_json(silent=True) or {}; status = data.get("status")
        if status not in ("approved", "rejected"): return jsonify(error="status must be approved or rejected."), 400
        item.status = status; item.comments = str(data.get("comments", "")).strip(); item.reviewed_by = current_user().id; item.reviewed_at = datetime.now(timezone.utc)
        if item.request_type == "equipment_borrowing" and item.reference_id:
            borrowing = db.session.get(BorrowingRequest, item.reference_id)
            if borrowing: borrowing.status = status
        db.session.add(Notification(user_id=item.requested_by, title="Approval updated", message=f"Approval #{item.id} was {status}."))
        log_change("approvals", "review", str(item.id), _approval_json(item)); db.session.commit()
        return jsonify(approval=_approval_json(item))

    @app.get("/api/notifications")
    @login_required
    def notifications():
        return jsonify(notifications=[{"id": n.id, "title": n.title, "message": n.message, "read": n.read_at is not None, "createdAt": n.created_at.isoformat()} for n in Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()])

    @app.patch("/api/notifications/<int:notification_id>/read")
    @login_required
    def read_notification(notification_id):
        item = db.session.get(Notification, notification_id)
        if not item or item.user_id != current_user().id: return jsonify(error="Notification not found."), 404
        item.read_at = datetime.now(timezone.utc); db.session.commit(); return jsonify(message="Notification marked as read.")

    @app.get("/api/suppliers")
    @login_required
    def suppliers():
        return jsonify(suppliers=[_supplier_json(item) for item in Supplier.query.order_by(Supplier.name).all()])

    @app.post("/api/suppliers")
    @admin_required
    def create_supplier():
        try:
            data = parse_json(); name = str(data.get("name", "")).strip()
            if not name: raise ValueError("name is required.")
            item = Supplier(name=name, contact_name=str(data.get("contactName", "")).strip(), email=str(data.get("email", "")).strip(), phone=str(data.get("phone", "")).strip(), address=str(data.get("address", "")).strip())
            db.session.add(item); db.session.flush(); log_change("suppliers", "add", name, _supplier_json(item)); db.session.commit()
            return jsonify(supplier=_supplier_json(item)), 201
        except ValueError as error:
            db.session.rollback(); return jsonify(error=str(error)), 400

    @app.patch("/api/suppliers/<int:supplier_id>")
    @admin_required
    def update_supplier(supplier_id):
        item = db.session.get(Supplier, supplier_id)
        if not item: return jsonify(error="Supplier not found."), 404
        data = request.get_json(silent=True) or {}
        for key, field in (("name", "name"), ("contactName", "contact_name"), ("email", "email"), ("phone", "phone"), ("address", "address"), ("status", "status")):
            if key in data: setattr(item, field, str(data[key]).strip())
        log_change("suppliers", "edit", item.name, data); db.session.commit(); return jsonify(supplier=_supplier_json(item))

    def _financial_routes(model, kind, path, required):
        @app.get(path, endpoint=f"{kind}_list")
        @login_required
        def list_records(model=model, kind=kind):
            return jsonify(**{f"{kind}s": [_financial_json(item, kind) for item in model.query.order_by(model.created_at.desc()).all()]})

        @app.post(path, endpoint=f"{kind}_create")
        @admin_required
        def create_record(model=model, kind=kind, required=required):
            try:
                data = parse_json()
                for field in required:
                    if data.get(field) in (None, ""): raise ValueError(f"{field} is required.")
                kwargs = {"amount": _amount(data.get("amount")), "created_by": current_user().id} if kind == "purchase" else {"amount": _amount(data.get("amount")), "submitted_by": current_user().id} if kind == "expense" else {"amount": _amount(data.get("amount")), "created_by": current_user().id}
                if kind == "purchase": kwargs.update(supplier_id=int(data["supplierId"]), description=str(data["description"]).strip(), purchase_date=_date(data["purchaseDate"], "purchaseDate"))
                elif kind == "expense": kwargs.update(category=str(data["category"]).strip(), description=str(data["description"]).strip(), expense_date=_date(data["expenseDate"], "expenseDate"))
                else: kwargs.update(name=str(data["name"]).strip(), category=str(data["category"]).strip(), period_start=_date(data["periodStart"], "periodStart"), period_end=_date(data["periodEnd"], "periodEnd"))
                item = model(**kwargs); db.session.add(item); db.session.flush(); log_change(kind, "add", str(item.id), _financial_json(item, kind)); db.session.commit()
                return jsonify(**{kind: _financial_json(item, kind)}), 201
            except (ValueError, TypeError) as error:
                db.session.rollback(); return jsonify(error=str(error)), 400
        return list_records, create_record

    _financial_routes(PurchaseRecord, "purchase", "/api/purchases", ("supplierId", "description", "amount", "purchaseDate"))
    _financial_routes(Expense, "expense", "/api/expenses", ("category", "description", "amount", "expenseDate"))
    _financial_routes(Budget, "budget", "/api/budgets", ("name", "category", "amount", "periodStart", "periodEnd"))

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

    @app.get("/api/places/search")
    @login_required
    def place_search():
        query = request.args.get("q", "").strip()
        if len(query) < 3 or len(query) > 160:
            return jsonify(places=[])
        try:
            search_url = os.environ.get("PLACE_SEARCH_URL", "https://nominatim.openstreetmap.org/search")
            url = search_url + "?format=jsonv2&limit=5&addressdetails=1&countrycodes=ph&q=" + quote(query)
            req = Request(url, headers={"User-Agent": os.environ.get("PLACE_SEARCH_USER_AGENT", "ITPC-ERP/1.0")})
            with urlopen(req, timeout=5) as response:
                results = json.load(response)
            philippines_results = [
                result
                for result in results
                if result.get("address", {}).get("country_code", "").lower() == "ph"
            ]
            return jsonify(
                places=[
                    {
                        "name": result.get("name") or result.get("display_name", "").split(",")[0],
                        "address": result.get("display_name", ""),
                        "latitude": float(result["lat"]),
                        "longitude": float(result["lon"]),
                        "mapUrl": "https://www.openstreetmap.org/?mlat=" + result["lat"] + "&mlon=" + result["lon"] + "#map=18/" + result["lat"] + "/" + result["lon"],
                    }
                    for result in philippines_results
                ]
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            app.logger.exception("Place search failed")
            return jsonify(error="Location search is temporarily unavailable."), 502

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
            event = Event(title=title, date=event_date, time=str(data.get("time", "")), event_type=str(data.get("type", "meeting")), location=location, address=str(data.get("address", "")).strip(), latitude=data.get("latitude"), longitude=data.get("longitude"), map_url=str(data.get("mapUrl", "")).strip(), description=str(data.get("description", "")).strip())
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
            for field in ("address", "mapUrl"):
                if field in data:
                    setattr(event, "map_url" if field == "mapUrl" else field, str(data[field]).strip())
            for field in ("latitude", "longitude"):
                if field in data:
                    setattr(event, field, data[field])
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
                event.address = str(payload.get("address", "")).strip()
                event.latitude = payload.get("latitude")
                event.longitude = payload.get("longitude")
                event.map_url = str(payload.get("mapUrl", "")).strip()
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
            db.session.add(Event(id=entry.record_id, title=record["title"], date=date.fromisoformat(record["date"]), time=record.get("time", ""), event_type=record.get("type", "meeting"), location=record["location"], address=record.get("address", ""), latitude=record.get("latitude"), longitude=record.get("longitude"), map_url=record.get("mapUrl", ""), description=record.get("description", "")))
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
