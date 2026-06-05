import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message
from channels.db import database_sync_to_async

import asyncio
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_group_name = f'chat_{ids[0]}_{ids[1]}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        await self.mark_messages_read(self.other_user_id, self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        if text_data_json.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_typing',
                    'sender_id': self.user.id,
                    'is_typing': text_data_json.get('is_typing', True)
                }
            )
            return
            
        message = text_data_json.get('message')
        if not message: return

        # 1. INSTANT BROADCAST — zero database latency!
        time_str = timezone.now().strftime('%H:%M')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': self.user.id,
                'time': time_str,
            }
        )

        # 2. Save to DB and push toast notification in the background
        asyncio.create_task(self.save_and_notify_background(message))

    async def save_and_notify_background(self, message):
        # Save message to database
        await self.save_message(self.user.id, self.other_user_id, message)

        # Trigger global pop-up notification toast
        try:
            avatar_url = self.user.profile.profile_image.url
        except Exception:
            avatar_url = '/static/images/default_profile.png'

        unread_msg = await self.get_unread_messages_count(self.other_user_id)

        await self.channel_layer.group_send(
            f'notif_{self.other_user_id}',
            {
                'type': 'notification_message',
                'notification_type': 'message',
                'sender_username': self.user.username,
                'sender_id': self.user.id,
                'sender_avatar': avatar_url,
                'message': message,
                'unread_count': unread_msg,
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        time = event['time']

        # Mark as read if receiving from someone else while connected
        if sender_id != self.user.id:
            await self.mark_messages_read(sender_id, self.user.id)

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message,
            'sender_id': sender_id,
            'time': time
        }))
        
    # Receive typing indicator from room group
    async def chat_typing(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, body):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        msg = Message.objects.create(sender=sender, receiver=receiver, body=body)
        return msg

    @database_sync_to_async
    def mark_messages_read(self, sender_id, receiver_id):
        Message.objects.filter(sender_id=sender_id, receiver_id=receiver_id, is_read=False).update(is_read=True)

    @database_sync_to_async
    def get_unread_messages_count(self, user_id):
        return Message.objects.filter(receiver_id=user_id, is_read=False).count()


# ─────────────────────────────────────────────────────────────────
# Notification Consumer — Real-time push per user
# ─────────────────────────────────────────────────────────────────
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        # Each user gets a personal group: notif_<user_id>
        self.group_name = f'notif_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle client-side messages (e.g. mark-read ping)."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'mark_read':
                await self.mark_all_read()
        except Exception:
            pass

    async def notification_message(self, event):
        """Called by channel layer when a notification is pushed to this user."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': event.get('notification_type'),
            'sender_username': event.get('sender_username'),
            'sender_id': event.get('sender_id'),
            'sender_avatar': event.get('sender_avatar'),
            'message': event.get('message'),
            'post_id': event.get('post_id'),
            'unread_count': event.get('unread_count', 1),
        }))

    @database_sync_to_async
    def mark_all_read(self):
        from .models import Notification
        Notification.objects.filter(receiver=self.user, is_read=False).update(is_read=True)


# ─────────────────────────────────────────────────────────────────
# Helper: push a notification event to a user's WS channel
# Call this from any Django view after creating a Notification.
# ─────────────────────────────────────────────────────────────────
def push_notification_to_user(receiver_id, sender, notification_type, post_id=None, unread_count=1):
    """
    Synchronous helper — calls async channel layer from sync Django views.
    Usage:
        push_notification_to_user(receiver.id, request.user, 'like', post_id=post.id)
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        # Build message text
        type_messages = {
            'like': f'{sender.username} liked your post',
            'comment': f'{sender.username} commented on your post',
            'follow': f'{sender.username} started following you',
            'follow_request': f'{sender.username} sent you a follow request',
            'follow_accept': f'{sender.username} accepted your follow request',
            'react': f'{sender.username} reacted to your post',
        }
        message = type_messages.get(notification_type, f'{sender.username} interacted with you')

        # Get sender avatar URL safely
        try:
            avatar_url = sender.profile.profile_image.url
        except Exception:
            avatar_url = '/static/images/default_profile.png'

        async_to_sync(channel_layer.group_send)(
            f'notif_{receiver_id}',
            {
                'type': 'notification_message',
                'notification_type': notification_type,
                'sender_username': sender.username,
                'sender_avatar': avatar_url,
                'message': message,
                'post_id': post_id,
                'unread_count': unread_count,
            }
        )
    except Exception as e:
        # Never crash the view if WS push fails
        import logging
        logging.getLogger(__name__).warning(f'WS notification push failed: {e}')
