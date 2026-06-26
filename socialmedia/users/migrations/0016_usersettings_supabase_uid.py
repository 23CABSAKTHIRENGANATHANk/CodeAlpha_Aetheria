from django.db import migrations, models


class Migration(migrations.Migration):
    """Add supabase_uid field to UserSettings for Supabase Auth integration."""

    dependencies = [
        ("users", "0015_delete_premiumuser"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="supabase_uid",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Supabase Auth UUID (auth.users.id). Set automatically on first Supabase sign-in.",
                max_length=36,
            ),
        ),
    ]
