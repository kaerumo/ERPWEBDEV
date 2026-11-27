import json
from datetime import date, time
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from erp.models import (
    ActivityEntry,
    AppConfiguration,
    ChangeLogEntry,
    CouncilEvent,
    InventoryItem,
    Officer,
)


COLLECTION_MODELS = {
    "inventory": InventoryItem,
    "officers": Officer,
    "events": CouncilEvent,
    "activity": ActivityEntry,
    "changelog": ChangeLogEntry,
}
COLLECTION_FIELDS = {
    "inventory": {"id", "name", "category", "quantity"},
    "officers": {"id", "name", "position", "committee", "status"},
    "events": {"id", "title", "date", "time", "location", "type", "description"},
    "activity": {"message", "type", "time"},
    "changelog": {"id", "time", "user", "role", "module", "action", "target", "details"},
}
MAX_REQUEST_BYTES = 2 * 1024 * 1024


class RevisionConflict(Exception):
    pass


def _role(user):
    return "admin" if user.is_staff or user.is_superuser else "member"


def _json_body(request):
    if len(request.body) > MAX_REQUEST_BYTES:
        raise ValueError("Request body is too large.")
    if request.content_type != "application/json":
        raise ValueError("Expected an application/json request.")
    try:
        return json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Request body must contain valid JSON.") from error


def _login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def _admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Administrator access required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


def _seed_defaults():
    with transaction.atomic():
        config = AppConfiguration.objects.select_for_update().get(key="initial_data")
        if config.value.get("seeded"):
            return

        if not InventoryItem.objects.exists():
            InventoryItem.objects.bulk_create(
                [
                    InventoryItem(name="ITPC Org T-Shirts (S-XL)", category="merchandise", quantity=35),
                    InventoryItem(name="Tarpaulins (event banners)", category="event-materials", quantity=2),
                    InventoryItem(name="Certificate holders", category="office-supplies", quantity=15),
                    InventoryItem(name="ITPC lanyards", category="merchandise", quantity=48),
                    InventoryItem(name="Extension cords", category="event-materials", quantity=4),
                    InventoryItem(name="Bond paper (reams)", category="office-supplies", quantity=12),
                ]
            )
        if not Officer.objects.exists():
            Officer.objects.bulk_create(
                [
                    Officer(name="Sample President", position="president", committee="Executive", status="active"),
                    Officer(name="Sample Officer A", position="committee-head", committee="Events", status="active"),
                    Officer(name="Sample Officer B", position="member", committee="Logistics", status="inactive"),
                    Officer(name="Sample Officer C", position="member", committee="Events", status="active"),
                    Officer(name="Sample Officer D", position="committee-head", committee="Logistics", status="active"),
                ]
            )
        if not CouncilEvent.objects.exists():
            today = timezone.localdate()
            CouncilEvent.objects.bulk_create(
                [
                    CouncilEvent(
                        title="General Assembly",
                        date=date.fromordinal(today.toordinal() + 2),
                        time=time(13, 0),
                        location="Main Auditorium",
                        type="meeting",
                        description="Semester kickoff with all officers and members.",
                    ),
                    CouncilEvent(
                        title="Web Dev Workshop",
                        date=date.fromordinal(today.toordinal() + 5),
                        time=time(9, 0),
                        location="Computer Lab 3",
                        type="workshop",
                        description="Hands-on HTML, CSS and JavaScript session.",
                    ),
                    CouncilEvent(
                        title="Officers Meeting",
                        date=date.fromordinal(today.toordinal() + 9),
                        time=time(16, 30),
                        location="ITPC Office",
                        type="meeting",
                        description="Budget and logistics planning.",
                    ),
                    CouncilEvent(
                        title="ITPC Night",
                        date=date.fromordinal(today.toordinal() + 16),
                        time=time(18, 0),
                        location="University Grounds",
                        type="social",
                        description="Annual org night with games and performances.",
                    ),
                    CouncilEvent(
                        title="Tech Talk: Careers in IT",
                        date=date.fromordinal(today.toordinal() - 4),
                        time=time(14, 0),
                        location="Room 204",
                        type="seminar",
                        description="Guest speakers from partner companies.",
                    ),
                ]
            )
        config.value = {"seeded": True}
        config.save(update_fields=["value"])


def _serialize(model, collection):
    result = []
    for row in model.objects.all():
        if collection == "inventory":
            result.append(
                {"id": row.pk, "name": row.name, "category": row.category, "quantity": row.quantity}
            )
        elif collection == "officers":
            result.append(
                {
                    "id": row.pk,
                    "name": row.name,
                    "position": row.position,
                    "committee": row.committee,
                    "status": row.status,
                }
            )
        elif collection == "events":
            result.append(
                {
                    "id": row.pk,
                    "title": row.title,
                    "date": row.date.isoformat(),
                    "time": row.time.strftime("%H:%M"),
                    "location": row.location,
                    "type": row.type,
                    "description": row.description,
                }
            )
        elif collection == "activity":
            result.append(
                {"message": row.message, "type": row.type, "time": row.time.isoformat()}
            )
        else:
            result.append(
                {
                    "id": row.pk,
                    "time": row.time.isoformat(),
                    "user": row.username,
                    "role": row.role,
                    "module": row.module,
                    "action": row.action,
                    "target": row.target,
                    "details": row.details,
                }
            )
    return result


def _validate_records(collection, records):
    if not isinstance(records, list):
        raise ValueError("The collection must be a list.")
    if len(records) > 5000:
        raise ValueError("A collection cannot contain more than 5,000 records.")

    allowed_fields = COLLECTION_FIELDS[collection]
    normalized = []
    used_ids = set()
    used_names = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index + 1} must be an object.")
        if set(record) - allowed_fields:
            raise ValueError(f"Record {index + 1} contains unsupported fields.")

        if collection == "inventory":
            name = _text(record, "name", 160)
            category = record.get("category")
            quantity = record.get("quantity")
            if category not in InventoryItem.Category.values:
                raise ValueError(f"Record {index + 1} has an invalid category.")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
                raise ValueError(f"Record {index + 1} quantity must be a non-negative whole number.")
            _check_unique_name(name, used_names, index)
            normalized.append(
                {"id": _record_id(record, used_ids, index), "name": name, "category": category, "quantity": quantity}
            )
        elif collection == "officers":
            name = _text(record, "name", 160)
            position = record.get("position")
            status = record.get("status")
            committee = _text(record, "committee", 120)
            if position not in Officer.Position.values or status not in Officer.Status.values:
                raise ValueError(f"Record {index + 1} has an invalid position or status.")
            _check_unique_name(name, used_names, index)
            normalized.append(
                {
                    "id": _record_id(record, used_ids, index),
                    "name": name,
                    "position": position,
                    "committee": committee,
                    "status": status,
                }
            )
        elif collection == "events":
            event_date = parse_date(_text(record, "date", 10))
            event_time = parse_time(_text(record, "time", 8))
            event_type = record.get("type")
            if not event_date or not event_time:
                raise ValueError(f"Record {index + 1} has an invalid date or time.")
            if event_type not in CouncilEvent.EventType.values:
                raise ValueError(f"Record {index + 1} has an invalid event type.")
            normalized.append(
                {
                    "id": _record_id(record, used_ids, index),
                    "title": _text(record, "title", 160),
                    "date": event_date,
                    "time": event_time,
                    "location": _text(record, "location", 160),
                    "type": event_type,
                    "description": _text(record, "description", 5000, allow_empty=True),
                }
            )
        elif collection == "activity":
            timestamp = parse_datetime(_text(record, "time", 40))
            if not timestamp:
                raise ValueError(f"Activity {index + 1} has an invalid timestamp.")
            normalized.append(
                {
                    "message": _text(record, "message", 300),
                    "type": _text(record, "type", 32),
                    "time": timestamp,
                }
            )
        else:
            timestamp = parse_datetime(_text(record, "time", 40))
            details = record.get("details")
            if not timestamp or not isinstance(details, list):
                raise ValueError(f"Change log entry {index + 1} has invalid time or details.")
            if len(details) > 32 or any(not isinstance(detail, dict) for detail in details):
                raise ValueError(f"Change log entry {index + 1} has invalid details.")
            normalized.append(
                {
                    "id": _record_id(record, used_ids, index, required=False),
                    "time": timestamp,
                    "username": _text(record, "user", 150, allow_empty=True),
                    "module": _text(record, "module", 32),
                    "action": _text(record, "action", 32),
                    "target": _text(record, "target", 300),
                    "details": details,
                }
            )
    return normalized


def _text(record, field, limit, allow_empty=False):
    value = record.get(field)
    if not isinstance(value, str):
        raise ValueError(f"'{field}' must be text.")
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError(f"'{field}' is required.")
    if len(value) > limit:
        raise ValueError(f"'{field}' must be at most {limit} characters.")
    return value


def _record_id(record, used_ids, index, required=True):
    value = record.get("id")
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"Record {index + 1} must have a positive integer id.")
    if value in used_ids:
        raise ValueError(f"Duplicate record id: {value}.")
    used_ids.add(value)
    return value


def _check_unique_name(name, used_names, index):
    normalized_name = name.casefold()
    if normalized_name in used_names:
        raise ValueError(f"Record {index + 1} has a duplicate name.")
    used_names.add(normalized_name)


def _replace_collection(collection, records, user, expected_revision):
    rows = _validate_records(collection, records)
    model = COLLECTION_MODELS[collection]
    with transaction.atomic():
        revision_record = AppConfiguration.objects.select_for_update().get(
            key="revision_" + collection
        )
        current_revision = revision_record.value["revision"]
        if current_revision != expected_revision:
            raise RevisionConflict
        model.objects.all().delete()
        if collection == "inventory":
            model.objects.bulk_create([InventoryItem(**row) for row in rows])
        elif collection == "officers":
            model.objects.bulk_create([Officer(**row) for row in rows])
        elif collection == "events":
            model.objects.bulk_create([CouncilEvent(**row) for row in rows])
        elif collection == "activity":
            model.objects.bulk_create([ActivityEntry(**row) for row in rows[:10]])
        else:
            entries = []
            for row in rows[:1000]:
                row_id = row.pop("id")
                entries.append(
                    ChangeLogEntry(
                        id=row_id,
                        user=user,
                        role=_role(user),
                        **row,
                    )
                )
            ChangeLogEntry.objects.bulk_create(entries)
        next_revision = current_revision + 1
        revision_record.value = {"revision": next_revision}
        revision_record.save(update_fields=["value"])
    return next_revision


@ensure_csrf_cookie
def frontend_page(request, page):
    page_name = page if page.endswith(".html") else page + ".html"
    if page_name != "index.html" and not request.user.is_authenticated:
        return redirect("/index.html")
    try:
        template = get_template(page_name)
    except TemplateDoesNotExist:
        return HttpResponse("Page not found.", status=404)
    return HttpResponse(template.render({}, request))


@require_http_methods(["GET"])
def session_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    user = request.user
    return JsonResponse(
        {
            "authenticated": True,
            "username": user.get_username(),
            "name": user.get_full_name() or user.get_username(),
            "role": _role(user),
        }
    )


@require_http_methods(["POST"])
def login_view(request):
    try:
        data = _json_body(request)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"error": "Enter a username and password."}, status=400)
    user = authenticate(request, username=username.strip(), password=password)
    if user is None:
        return JsonResponse({"error": "Invalid username or password."}, status=401)
    login(request, user)
    return JsonResponse(
        {
            "authenticated": True,
            "username": user.get_username(),
            "name": user.get_full_name() or user.get_username(),
            "role": _role(user),
        }
    )


@require_http_methods(["POST"])
@_login_required
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
@_login_required
def data_view(request):
    _seed_defaults()
    with transaction.atomic():
        revision_records = AppConfiguration.objects.select_for_update().filter(
            key__startswith="revision_"
        ).order_by("key")
        revisions = {
            record.key.removeprefix("revision_"): record.value["revision"]
            for record in revision_records
        }
        data = {
            collection: _serialize(model, collection)
            for collection, model in COLLECTION_MODELS.items()
        }
    data["_revisions"] = revisions
    return JsonResponse(data)


@require_http_methods(["PUT"])
@_admin_required
def collection_view(request, collection):
    if collection not in COLLECTION_MODELS:
        return JsonResponse({"error": "Unknown data collection."}, status=404)
    revision_header = request.headers.get("If-Match", "")
    if (
        not revision_header
        or len(revision_header) > 12
        or not revision_header.isascii()
        or not revision_header.isdecimal()
    ):
        return JsonResponse({"error": "A data revision is required."}, status=428)
    try:
        records = _json_body(request)
        revision = _replace_collection(
            collection,
            records,
            request.user,
            int(revision_header),
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except RevisionConflict:
        return JsonResponse(
            {"error": "This collection changed in another session. Reload before editing."},
            status=409,
        )
    except IntegrityError:
        return JsonResponse({"error": "The data conflicts with an existing record."}, status=400)
    return JsonResponse({"ok": True, "count": len(records), "revision": revision})
