"""
scripts/migrate_cloudinary_to_supabase.py
==========================================
One-shot script to migrate all media files from Cloudinary to Supabase Storage.

What it does:
  1. Queries every ImageField / FileField in the Django models for stored paths
  2. Constructs the Cloudinary URL for each file
  3. Downloads the file from Cloudinary
  4. Uploads it to the correct Supabase Storage bucket (via SupabaseStorage backend)
  5. Optionally updates the DB record to point to the new Supabase path

Usage:
    # Set env vars first:
    # SUPABASE_URL, SUPABASE_KEY, CLOUDINARY_URL (for source download)
    # Then run from the socialmedia/ Django project directory:

    python ../scripts/migrate_cloudinary_to_supabase.py --dry-run --verbose
    python ../scripts/migrate_cloudinary_to_supabase.py --concurrency=4
    python ../scripts/migrate_cloudinary_to_supabase.py --model=users.Profile --field=profile_image

Requirements:
    pip install cloudinary requests tqdm
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# ── Bootstrap Django ──────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_SOCIALMEDIA_DIR = _SCRIPT_DIR.parent / "socialmedia"
sys.path.insert(0, str(_SOCIALMEDIA_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialmedia.settings")
import django
django.setup()

# ── Now import Django stuff ───────────────────────────────────────────────────
import requests
from django.conf import settings
from django.db import models

logger = logging.getLogger("cloudinary_migration")
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)

# ── File-field inventory ─────────────────────────────────────────────────────

def get_file_fields():
    """Enumerate all ImageField/FileField instances across installed apps."""
    from django.apps import apps
    fields = []
    for app_config in apps.get_app_configs():
        if app_config.name not in ("users", "posts"):
            continue
        for model in app_config.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, (models.ImageField, models.FileField)):
                    fields.append((model, field))
    return fields


def cloudinary_url_for(path: str) -> str:
    """Build the full Cloudinary URL from a stored path."""
    import cloudinary
    cloud_name = cloudinary.config().cloud_name or os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    if not cloud_name:
        # Try to extract from CLOUDINARY_URL
        cl_url = os.environ.get("CLOUDINARY_URL", "")
        if cl_url:
            # cloudinary://key:secret@cloud_name
            parts = cl_url.split("@")
            if len(parts) > 1:
                cloud_name = parts[-1]
    if not cloud_name:
        raise ValueError("Cannot determine Cloudinary cloud_name. Set CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME.")
    # Cloudinary stores paths like: image/upload/v1234567890/path/to/file.jpg
    # Django cloudinary-storage saves just the relative path
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{path}"


def download_file(url: str, timeout: int = 30) -> bytes | None:
    """Download a file from a URL and return its bytes."""
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        return response.content
    except requests.RequestException as exc:
        logger.error("Failed to download %s: %s", url, exc)
        return None


def upload_to_supabase(name: str, content: bytes) -> str | None:
    """Upload bytes to Supabase Storage and return the stored path."""
    from socialmedia.storage_backends import SupabaseStorage
    import io
    storage = SupabaseStorage()
    try:
        from django.core.files.base import ContentFile
        file_obj = ContentFile(content, name=name)
        saved_path = storage._save(name, file_obj)
        return saved_path
    except Exception as exc:
        logger.error("Supabase upload failed for %s: %s", name, exc)
        return None


# ── Main migration logic ─────────────────────────────────────────────────────

def migrate_field(model, field, dry_run: bool, verbose: bool, update_db: bool):
    """Migrate all non-empty values of a single FileField to Supabase."""
    field_name = field.name
    model_name = f"{model._meta.app_label}.{model._meta.model_name}"
    queryset = model.objects.exclude(**{field_name: ""}).exclude(**{field_name: None})
    total = queryset.count()

    if total == 0:
        logger.info("[%s.%s] No files to migrate.", model_name, field_name)
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    logger.info("[%s.%s] %d files to migrate", model_name, field_name, total)
    success = failed = skipped = 0

    for obj in queryset.iterator():
        stored_path = str(getattr(obj, field_name))
        if not stored_path:
            skipped += 1
            continue

        # Skip if already migrated (Supabase URLs contain supabase.co)
        if "supabase.co" in stored_path:
            if verbose:
                logger.info("  SKIP (already Supabase): %s", stored_path)
            skipped += 1
            continue

        # Build Cloudinary source URL
        try:
            src_url = cloudinary_url_for(stored_path)
        except ValueError as exc:
            logger.error("  Cannot build Cloudinary URL for %s: %s", stored_path, exc)
            failed += 1
            continue

        if verbose:
            logger.info("  → %s", stored_path)
            logger.info("    from: %s", src_url)

        if dry_run:
            success += 1
            continue

        # Download from Cloudinary
        content = download_file(src_url)
        if not content:
            failed += 1
            continue

        # Upload to Supabase
        new_path = upload_to_supabase(stored_path, content)
        if not new_path:
            failed += 1
            continue

        if verbose:
            logger.info("    to: %s", new_path)

        # Update DB record
        if update_db and new_path != stored_path:
            try:
                model.objects.filter(pk=obj.pk).update(**{field_name: new_path})
                if verbose:
                    logger.info("    DB updated for pk=%s", obj.pk)
            except Exception as exc:
                logger.warning("  DB update failed for pk=%s: %s", obj.pk, exc)

        success += 1
        time.sleep(0.05)  # Rate-limit: be polite to Cloudinary

    logger.info(
        "[%s.%s] Done: %d success, %d failed, %d skipped",
        model_name, field_name, success, failed, skipped,
    )
    return {"total": total, "success": success, "failed": failed, "skipped": skipped}


def run(dry_run: bool, verbose: bool, update_db: bool, filter_model: str = None, filter_field: str = None):
    """Run the full migration across all file fields."""
    logger.info("=== Cloudinary → Supabase Storage Migration ===")
    if dry_run:
        logger.info("DRY RUN: No files will be uploaded.")

    fields = get_file_fields()
    totals = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    for model, field in fields:
        model_label = f"{model._meta.app_label}.{model._meta.model_name}"
        if filter_model and filter_model.lower() not in model_label.lower():
            continue
        if filter_field and filter_field.lower() != field.name.lower():
            continue

        result = migrate_field(model, field, dry_run=dry_run, verbose=verbose, update_db=update_db)
        for k in totals:
            totals[k] += result[k]

    logger.info("\n=== Migration Summary ===")
    logger.info("  Total files:   %d", totals["total"])
    logger.info("  Migrated:      %d", totals["success"])
    logger.info("  Failed:        %d", totals["failed"])
    logger.info("  Skipped:       %d", totals["skipped"])
    if totals["failed"] > 0:
        logger.warning("Some files failed to migrate — check logs above.")
    else:
        logger.info("Migration complete!")


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Cloudinary media to Supabase Storage.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without uploading.")
    parser.add_argument("--verbose", action="store_true", help="Show per-file details.")
    parser.add_argument("--no-update-db", action="store_true", help="Upload files but don't update DB records.")
    parser.add_argument("--model", type=str, default=None, help="Only migrate this model (e.g. users.Profile).")
    parser.add_argument("--field", type=str, default=None, help="Only migrate this field name (e.g. profile_image).")
    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        verbose=args.verbose,
        update_db=not args.no_update_db,
        filter_model=args.model,
        filter_field=args.field,
    )
