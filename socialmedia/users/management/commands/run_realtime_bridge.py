"""
Management command: run_realtime_bridge
========================================
Starts the Supabase Realtime bridge as a long-running async process.
Subscribes to Postgres table changes and forwards them to Django Channels.

Usage:
    python manage.py run_realtime_bridge
    python manage.py run_realtime_bridge --tables=users_notification,users_message

Run this in a separate process/worker on your server:
    Render: Add as a Background Worker in render.yaml
    Local:  Open a second terminal and run this command
"""

import asyncio
import logging
import os
import signal

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Supabase Realtime → Django Channels bridge (long-running async process)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tables",
            type=str,
            default=None,
            help="Comma-separated list of tables to subscribe to (default: all configured tables).",
        )

    def handle(self, *args, **options):
        supabase_url = os.environ.get("SUPABASE_URL")
        if not supabase_url:
            self.stderr.write(self.style.ERROR(
                "SUPABASE_URL is not set. Cannot start Realtime bridge."
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== Aetheria Supabase Realtime Bridge ===\n"
            f"Connecting to: {supabase_url}\n"
        ))

        from socialmedia.realtime_bridge import SupabaseRealtimeBridge

        bridge = SupabaseRealtimeBridge()

        # Handle graceful shutdown on SIGINT/SIGTERM
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def _shutdown(sig, frame):
            self.stdout.write(self.style.WARNING("\nShutting down Realtime bridge..."))
            loop.create_task(bridge.stop())

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            loop.run_until_complete(bridge.start())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bridge stopped."))
        finally:
            loop.close()

        self.stdout.write(self.style.SUCCESS("Realtime bridge exited cleanly."))
