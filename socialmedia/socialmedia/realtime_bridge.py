"""
Supabase Realtime Bridge for Aetheria
======================================
Server-side bridge that subscribes to Supabase Postgres Realtime changes
and forwards them to connected WebSocket clients via Django Channels.

This complements the client-side supabase-realtime.js by handling server-driven
cases (e.g., notifying users who are already in a WS session without requiring
client-side Supabase SDK).

Architecture:
    Supabase Realtime (postgres_changes)
        → SupabaseRealtimeBridge (this module)
            → Django Channels channel_layer.group_send()
                → NotificationConsumer.notification_message()
                    → Browser WebSocket

Usage:
    # Start the bridge as a background coroutine (in ASGI lifespan or management command)
    from socialmedia.realtime_bridge import SupabaseRealtimeBridge
    bridge = SupabaseRealtimeBridge()
    await bridge.start()   # blocks — run in asyncio.create_task()

    # Or via management command:
    python manage.py run_realtime_bridge

Configuration:
    SUPABASE_URL         — your Supabase project URL
    SUPABASE_KEY         — service-role key (NOT anon key)
    SUPABASE_JWT_SECRET  — used to authenticate the Realtime connection
"""

import asyncio
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

# Tables to subscribe to and their channel group routing
SUBSCRIPTIONS = [
    {
        "table": "users_notification",
        "event": "INSERT",
        # Route to notif_<receiver_id> group in Channels
        "group_fn": lambda record: f"notif_{record.get('receiver_id')}",
        "message_type": "notification_message",
        "payload_fn": lambda record: {
            "type": "notification_message",
            "notification_type": record.get("notification_type", ""),
            "sender_id": record.get("sender_id"),
            "post_id": record.get("post_id"),
            "is_read": record.get("is_read", False),
            "created_at": str(record.get("created_at", "")),
            "unread_count": 1,  # Client will fetch real count
        },
    },
    {
        "table": "users_message",
        "event": "INSERT",
        # Route to the receiver's notification group
        "group_fn": lambda record: f"notif_{record.get('receiver_id')}",
        "message_type": "new_message_notification",
        "payload_fn": lambda record: {
            "type": "new_message_notification",
            "sender_id": record.get("sender_id"),
            "chat_room_id": record.get("chat_room_id"),
            "body_preview": (record.get("body") or "")[:80],
            "created_at": str(record.get("created_at", "")),
        },
    },
]


class SupabaseRealtimeBridge:
    """Listens to Supabase Postgres Realtime and forwards to Django Channels.

    Uses the `realtime` Python library (pip install realtime>=1.0.0).
    Reconnects automatically on failure with exponential backoff.
    """

    def __init__(self):
        self.url = getattr(settings, "SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
        self.key = getattr(settings, "SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        self._running = False
        self._client = None

    async def start(self):
        """Start the Realtime bridge. Blocks until stopped."""
        if not self.url or not self.key:
            logger.warning(
                "SupabaseRealtimeBridge: SUPABASE_URL or SUPABASE_KEY not set — bridge disabled."
            )
            return

        self._running = True
        backoff = 1.0

        while self._running:
            try:
                logger.info("SupabaseRealtimeBridge: connecting to %s", self.url)
                await self._connect_and_listen()
                backoff = 1.0  # Reset on clean disconnect
            except Exception as exc:
                logger.error("SupabaseRealtimeBridge: error — %s. Reconnecting in %.0fs.", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def stop(self):
        """Gracefully stop the bridge."""
        self._running = False
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass

    async def _connect_and_listen(self):
        """Establish Supabase Realtime connection and register channel subscriptions."""
        try:
            from realtime import AsyncRealtimeClient
        except ImportError:
            logger.error(
                "SupabaseRealtimeBridge: 'realtime' package not installed. "
                "Run: pip install realtime>=1.0.0"
            )
            self._running = False
            return

        # Supabase Realtime endpoint: wss://xxx.supabase.co/realtime/v1/websocket
        realtime_url = self.url.replace("https://", "wss://").replace("http://", "ws://")
        realtime_url = realtime_url.rstrip("/") + "/realtime/v1/websocket"

        self._client = AsyncRealtimeClient(
            realtime_url,
            token=self.key,
            auto_reconnect=False,  # We handle reconnect ourselves
        )

        await self._client.connect()
        logger.info("SupabaseRealtimeBridge: connected")

        # Register one Realtime channel per table subscription
        for sub in SUBSCRIPTIONS:
            await self._register_subscription(sub)

        # Keep the connection alive
        await self._client.listen()

    async def _register_subscription(self, sub: dict):
        """Register a single postgres_changes subscription."""
        channel_name = f"aetheria-bridge-{sub['table']}"
        channel = self._client.channel(channel_name)

        def _on_change(payload):
            """Callback fired when Supabase emits a matching change event."""
            try:
                record = payload.get("record") or payload.get("new") or {}
                group = sub["group_fn"](record)
                message = sub["payload_fn"](record)

                if group and group.endswith("_None"):
                    # No valid receiver_id — skip
                    return

                # Forward to Django Channels (run in the event loop)
                asyncio.ensure_future(self._forward_to_channels(group, message))
            except Exception as exc:
                logger.warning("SupabaseRealtimeBridge: callback error for %s: %s", sub["table"], exc)

        channel.on_postgres_changes(
            event=sub["event"],
            schema="public",
            table=sub["table"],
            callback=_on_change,
        )

        await channel.subscribe()
        logger.info("SupabaseRealtimeBridge: subscribed to %s.%s (%s)", "public", sub["table"], sub["event"])

    @staticmethod
    async def _forward_to_channels(group: str, message: dict):
        """Send a message to a Django Channels group."""
        try:
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                await channel_layer.group_send(group, message)
                logger.debug("SupabaseRealtimeBridge: forwarded %s → %s", message.get("type"), group)
        except Exception as exc:
            logger.warning("SupabaseRealtimeBridge: Channels group_send failed: %s", exc)
