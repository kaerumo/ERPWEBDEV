import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTO_CREATE_SCHEMA"] = "1"

from app import event_json, officer_json


class EventStub:
    id = 4
    title = "Workshop"
    date = __import__("datetime").date(2026, 11, 3)
    time = "09:00"
    event_type = "workshop"
    location = "Lab 3"
    description = "Demo"


class OfficerStub:
    id = 2
    name = "Sample Officer"
    position = "member"
    committee = "Events"
    status = "active"


def test_event_json_matches_frontend_contract():
    assert event_json(EventStub()) == {
        "id": 4,
        "title": "Workshop",
        "date": "2026-11-03",
        "time": "09:00",
        "type": "workshop",
        "location": "Lab 3",
        "description": "Demo",
    }


def test_officer_json_matches_frontend_contract():
    assert officer_json(OfficerStub()) == {
        "id": 2,
        "name": "Sample Officer",
        "position": "member",
        "committee": "Events",
        "status": "active",
    }
