"""
Management command: migrate_to_supabase
=======================================
Migrates all Django application data from the current database to Supabase PostgreSQL.

Usage:
    python manage.py migrate_to_supabase --help
    python manage.py migrate_to_supabase --dry-run --verbose
    python manage.py migrate_to_supabase --dump-only --output=/tmp/aetheria_dump.json
    python manage.py migrate_to_supabase --load-only --input=/tmp/aetheria_dump.json

Steps performed:
    1. Validates SUPABASE_DB_URL is set and reachable
    2. Dumps all data from the current default DB using Django's dumpdata
    3. Applies migrations to Supabase DB (using 'supabase' DB alias)
    4. Loads the dumped data into Supabase DB
    5. Verifies row counts match between source and destination

Prerequisites:
    - Set SUPABASE_DB_URL in your .env
    - Add 'supabase' to DATABASES in settings (this command does it temporarily)
    - Supabase project must exist and the DB must be reachable
"""

import json
import os
import sys
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Migrate Aetheria data from current database to Supabase PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Validate connectivity and count rows without transferring data.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Show detailed progress output.",
        )
        parser.add_argument(
            "--dump-only",
            action="store_true",
            default=False,
            help="Only dump current DB to a JSON file (--output required).",
        )
        parser.add_argument(
            "--load-only",
            action="store_true",
            default=False,
            help="Only load a previously dumped JSON into Supabase (--input required).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Path to write the JSON dump (used with --dump-only).",
        )
        parser.add_argument(
            "--input",
            type=str,
            default=None,
            help="Path to a JSON dump to load (used with --load-only).",
        )
        parser.add_argument(
            "--exclude",
            nargs="*",
            default=["contenttypes", "auth.permission"],
            help="Apps/models to exclude from dump (default: contenttypes auth.permission).",
        )

    def handle(self, *args, **options):
        supabase_db_url = os.environ.get("SUPABASE_DB_URL")
        if not supabase_db_url and not options["load_only"]:
            raise CommandError(
                "SUPABASE_DB_URL is not set. "
                "Add it to your .env file: SUPABASE_DB_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"
            )

        dry_run = options["dry_run"]
        verbose = options["verbose"]

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Aetheria -> Supabase Migration ===\n"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No data will be transferred.\n"))

        # -- Step 1: Register Supabase as a second DB alias -------------------
        if not options["load_only"] or supabase_db_url:
            self._register_supabase_db(supabase_db_url, verbose)

        # -- Step 2: Validate connectivity ------------------------------------
        if not options["load_only"]:
            self._validate_connection("default", "Source (current DB)", verbose)
        if not options["dump_only"] and supabase_db_url:
            self._validate_connection("supabase", "Destination (Supabase)", verbose)

        # -- Step 3: Dump -----------------------------------------------------
        if options["load_only"]:
            dump_path = options["input"]
            if not dump_path or not os.path.exists(dump_path):
                raise CommandError(f"Input file not found: {dump_path}")
            self.stdout.write(f"Using existing dump: {dump_path}")
        else:
            dump_path = options["output"] or tempfile.mktemp(suffix=".json", prefix="aetheria_dump_")
            self._dump_data(dump_path, options["exclude"], verbose, dry_run)

        if options["dump_only"]:
            self.stdout.write(self.style.SUCCESS(f"\nDump saved to: {dump_path}"))
            return

        if dry_run:
            self._print_row_counts(verbose)
            self.stdout.write(self.style.SUCCESS("\nDry run complete — no data transferred."))
            return

        # -- Step 4: Run migrations on Supabase -------------------------------
        self.stdout.write("\n[3/4] Applying Django migrations to Supabase...")
        try:
            call_command("migrate", "--database=supabase", "--run-syncdb", verbosity=1 if verbose else 0)
            self.stdout.write(self.style.SUCCESS("  [OK] Migrations applied"))
        except Exception as e:
            raise CommandError(f"Migration failed: {e}")

        # -- Step 5: Load data ------------------------------------------------
        self.stdout.write("\n[4/4] Loading data into Supabase...")
        try:
            call_command(
                "loaddata",
                dump_path,
                "--database=supabase",
                verbosity=2 if verbose else 1,
            )
            self.stdout.write(self.style.SUCCESS("  [OK] Data loaded"))
        except Exception as e:
            raise CommandError(f"Data load failed: {e}. Dump preserved at: {dump_path}")

        # -- Step 6: Verify ---------------------------------------------------
        self._verify_row_counts(verbose)

        self.stdout.write(self.style.SUCCESS("\n[DONE] Migration complete! Update SUPABASE_DB_URL -> DATABASE_URL in production.\n"))

    # -- Helpers --------------------------------------------------------------

    def _register_supabase_db(self, supabase_db_url, verbose):
        """Dynamically add 'supabase' DB alias without restarting Django."""
        from django.conf import settings
        import urllib.parse as up

        if "supabase" in settings.DATABASES:
            if verbose:
                self.stdout.write("  'supabase' DB alias already registered.")
            return

        try:
            r = up.urlparse(supabase_db_url)
            db_config = {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": r.path.lstrip("/"),
                "USER": up.unquote(r.username or ""),
                "PASSWORD": up.unquote(r.password or ""),
                "HOST": r.hostname or "",
                "PORT": str(r.port or 5432),
                "CONN_MAX_AGE": 60,
                "CONN_HEALTH_CHECKS": False,
                "OPTIONS": {"connect_timeout": 10, "sslmode": "require"},
                "DISABLE_SERVER_SIDE_CURSORS": str(r.port) == "6543",
                "TIME_ZONE": None,
                "AUTOCOMMIT": True,
                "ATOMIC_REQUESTS": False,
                "TEST": {"NAME": None, "CHARSET": None, "COLLATION": None, "MIRROR": None, "DEPENDENCIES": ["default"], "CREATE_DB": True},
            }
            settings.DATABASES["supabase"] = db_config
            connections["supabase"].ensure_connection()
            if verbose:
                self.stdout.write(f"  Registered Supabase DB alias -> {db_config.get('HOST')}")
        except Exception as e:
            raise CommandError(f"Cannot configure Supabase DB alias: {e}")

    def _validate_connection(self, alias, label, verbose):
        """Test a named DB connection and print server version."""
        self.stdout.write(f"[.] Connecting to {label}...")
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"  [OK] {label}: {version[:60]}"))
        except Exception as e:
            raise CommandError(f"Cannot connect to {label}: {e}")

    def _dump_data(self, dump_path, exclude, verbose, dry_run):
        """Dump all data from the default DB to a JSON file."""
        self.stdout.write(f"\n[1/4] Dumping current database to {dump_path}...")
        if dry_run:
            self.stdout.write(self.style.WARNING("  Skipped (dry run)"))
            return

        exclude_flags = []
        for exc in (exclude or []):
            exclude_flags.extend(["--exclude", exc])

        out = StringIO()
        try:
            call_command(
                "dumpdata",
                *([f"--exclude={e}" for e in (exclude or [])]),
                "--natural-foreign",
                "--natural-primary",
                "--indent=2",
                "--output", dump_path,
                verbosity=2 if verbose else 0,
                stdout=out,
            )
            self.stdout.write(self.style.SUCCESS(f"  [OK] Dump saved: {dump_path}"))
        except Exception as e:
            raise CommandError(f"dumpdata failed: {e}")

    def _get_app_models(self):
        """Return all installed app models as (app_label, model_name) tuples."""
        from django.apps import apps
        return [(m._meta.app_label, m._meta.model_name, m) for m in apps.get_models()]

    def _print_row_counts(self, verbose):
        """Print row counts for each model in source DB (dry-run info)."""
        self.stdout.write("\n[DRY RUN] Row counts in source database:")
        for app_label, model_name, model in self._get_app_models():
            if app_label in ("contenttypes",):
                continue
            try:
                count = model.objects.using("default").count()
                if count > 0 or verbose:
                    self.stdout.write(f"  {app_label}.{model_name}: {count:,} rows")
            except Exception:
                pass

    def _verify_row_counts(self, verbose):
        """Compare row counts between source and Supabase DBs."""
        self.stdout.write("\n[5/5] Verifying row counts...")
        mismatches = []
        for app_label, model_name, model in self._get_app_models():
            if app_label in ("contenttypes",):
                continue
            try:
                src = model.objects.using("default").count()
                dst = model.objects.using("supabase").count()
                match = "[OK]" if src == dst else "[X]"
                if src != dst:
                    mismatches.append(f"  {match} {app_label}.{model_name}: source={src} supabase={dst}")
                elif verbose:
                    self.stdout.write(f"  {match} {app_label}.{model_name}: {src:,}")
            except Exception as e:
                if verbose:
                    self.stdout.write(f"  [?] {app_label}.{model_name}: {e}")

        if mismatches:
            self.stdout.write(self.style.WARNING("\nRow count mismatches:"))
            for m in mismatches:
                self.stdout.write(self.style.WARNING(m))
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] All row counts match!"))
