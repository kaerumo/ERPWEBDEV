from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class InventoryItem(models.Model):
    class Category(models.TextChoices):
        MERCHANDISE = "merchandise", "Merchandise"
        EVENT_MATERIALS = "event-materials", "Event materials"
        OFFICE_SUPPLIES = "office-supplies", "Office supplies"

    name = models.CharField(max_length=160)
    category = models.CharField(max_length=32, choices=Category.choices)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="inventory_name_case_insensitive_unique")
        ]

    def __str__(self):
        return self.name


class Officer(models.Model):
    class Position(models.TextChoices):
        PRESIDENT = "president", "President"
        COMMITTEE_HEAD = "committee-head", "Committee head"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=160)
    position = models.CharField(max_length=32, choices=Position.choices)
    committee = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=Status.choices)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class CouncilEvent(models.Model):
    class EventType(models.TextChoices):
        MEETING = "meeting", "Meeting"
        WORKSHOP = "workshop", "Workshop"
        SEMINAR = "seminar", "Seminar"
        SOCIAL = "social", "Social"

    title = models.CharField(max_length=160)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=EventType.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["date", "time", "id"]

    def __str__(self):
        return self.title


class ActivityEntry(models.Model):
    message = models.CharField(max_length=300)
    type = models.CharField(max_length=32)
    time = models.DateTimeField()

    class Meta:
        ordering = ["-time", "-id"]


class ChangeLogEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    username = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=16)
    time = models.DateTimeField()
    module = models.CharField(max_length=32)
    action = models.CharField(max_length=32)
    target = models.CharField(max_length=300)
    details = models.JSONField(default=list)

    class Meta:
        ordering = ["-time", "-id"]


class AppConfiguration(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.JSONField(default=dict)
