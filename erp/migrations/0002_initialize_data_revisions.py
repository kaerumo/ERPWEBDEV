from django.db import migrations


def initialize_data_revisions(apps, schema_editor):
    configuration = apps.get_model("erp", "AppConfiguration")
    configuration.objects.get_or_create(
        key="initial_data",
        defaults={"value": {"seeded": False}},
    )
    for collection in ("inventory", "officers", "events", "activity", "changelog"):
        configuration.objects.get_or_create(
            key="revision_" + collection,
            defaults={"value": {"revision": 0}},
        )


class Migration(migrations.Migration):
    dependencies = [("erp", "0001_initial")]

    operations = [
        migrations.RunPython(initialize_data_revisions, migrations.RunPython.noop),
    ]
