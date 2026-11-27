from django.contrib import admin

from erp.models import ActivityEntry, ChangeLogEntry, CouncilEvent, InventoryItem, Officer


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "committee", "status")
    list_filter = ("position", "committee", "status")
    search_fields = ("name", "committee")


@admin.register(CouncilEvent)
class CouncilEventAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "time", "type", "location")
    list_filter = ("type", "date")
    search_fields = ("title", "location")


admin.site.register(ActivityEntry)
admin.site.register(ChangeLogEntry)
