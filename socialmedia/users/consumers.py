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

        # Mark messages read on connect
        seen_msg_ids = await self.mark_messages_read(self.other_user_id, self.user.id)
        if seen_msg_ids:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_seen',
                    'seen_by': self.user.id,
                    'message_ids': seen_msg_ids
                }
            )

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

        # 1. Save to DB with proper initial status
        msg_id, initial_status = await self.create_and_save_message(self.user.id, self.other_user_id, message)

        # 2. BROADCAST to room group
        time_str = timezone.now().strftime('%H:%M')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': msg_id,
                'message': message,
                'sender_id': self.user.id,
                'time': time_str,
                'status': initial_status
            }
        )

        # 3. Save and push toast notification in the background
        asyncio.create_task(self.save_and_notify_background(message, msg_id))

    async def save_and_notify_background(self, message, message_id):
        # Trigger global pop-up notification toast
        try:
            avatar_url = self.user.profile.profile_image.url
        except Exception:
            avatar_url = '/static/images/default_profile.png'

        unread_msg = await self.get_unread_messages_count(self.other_user_id)

        try:
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'WS group_send failed: {e}')

        # Trigger Native Firebase Push
        await self.send_firebase_push(self.other_user_id, self.user, message)

    @database_sync_to_async
    def send_firebase_push(self, receiver_id, sender, body):
        try:
            from .utils import send_push_notification
            receiver_user = User.objects.get(id=receiver_id)
            send_push_notification(
                user=receiver_user,
                title=f"New message from {sender.username}",
                body=body,
                data={'notification_type': 'message', 'sender_id': str(sender.id)}
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Firebase push failed: {e}')

    # Receive message from room group
    async def chat_message(self, event):
        message_id = event.get('message_id')
        message = event['message']
        sender_id = event['sender_id']
        time = event['time']
        status = event.get('status', 'sent')

        # If I am the receiver, and I am actively connected to this room,
        # then I have seen this message!
        if sender_id != self.user.id:
            await self.update_message_status(message_id, 'seen')
            status = 'seen'
            # Notify the sender that it is seen in real-time
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_seen',
                    'seen_by': self.user.id,
                    'message_ids': [message_id]
                }
            )

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': message_id,
            'message': message,
            'sender_id': sender_id,
            'time': time,
            'status': status
        }))
        
    # Receive typing indicator from room group
    async def chat_typing(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'is_typing': event['is_typing']
        }))

    # Receive messages seen notification from room group
    async def messages_seen(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_seen',
            'seen_by': event['seen_by'],
            'message_ids': event['message_ids']
        }))

    @database_sync_to_async
    def create_and_save_message(self, sender_id, receiver_id, body):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        is_online = receiver.profile.is_online
        initial_status = 'delivered' if is_online else 'sent'
        msg = Message.objects.create(
            sender=sender, receiver=receiver, body=body, status=initial_status, is_read=(initial_status == 'seen')
        )
        return msg.id, initial_status

    @database_sync_to_async
    def update_message_status(self, message_id, status):
        try:
            msg = Message.objects.get(id=message_id)
            msg.status = status
            if status == 'seen':
                msg.is_read = True
            msg.save(update_fields=['status', 'is_read'])
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_messages_read(self, sender_id, receiver_id):
        unread_msgs = Message.objects.filter(sender_id=sender_id, receiver_id=receiver_id).exclude(status='seen')
        msg_ids = list(unread_msgs.values_list('id', flat=True))
        if msg_ids:
            unread_msgs.update(is_read=True, status='seen')
        return msg_ids

    @database_sync_to_async
    def get_unread_messages_count(self, user_id):
        return Message.objects.filter(receiver_id=user_id).exclude(status='seen').count()


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
        
        # Join global status group to receive other users' status changes
        self.status_group = 'online_status'
        await self.channel_layer.group_add(self.status_group, self.channel_name)

        await self.accept()

        # Update status in DB
        await self.update_user_online_status(True)

        # Broadcast online status
        await self.channel_layer.group_send(
            self.status_group,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'status': 'online'
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
        if hasattr(self, 'status_group'):
            # Update status in DB first
            await self.update_user_online_status(False)
            
            # Broadcast offline status along with last_seen
            from django.utils import timezone
            last_seen_str = timezone.now().strftime('%d %b, %H:%M')
            await self.channel_layer.group_send(
                self.status_group,
                {
                    'type': 'user_status_change',
                    'user_id': self.user.id,
                    'status': 'offline',
                    'last_seen': last_seen_str
                }
            )
            await self.channel_layer.group_discard(self.status_group, self.channel_name)

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

    async def user_status_change(self, event):
        """Called when another user goes online or offline."""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'status': event['status'],
                'last_seen': event.get('last_seen', '')
            }))

    @database_sync_to_async
    def update_user_online_status(self, is_online):
        from django.utils import timezone
        try:
            profile = self.user.profile
            profile.is_online = is_online
            profile.last_seen = timezone.now()
            profile.save(update_fields=['is_online', 'last_seen'])
        except Exception:
            pass

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

        try:
            async_to_sync(channel_layer.group_send)(
                f'notif_{receiver_id}',
                {
                    'type': 'notification_message',
                    'notification_type': notification_type,
                    'sender_username': sender.username,
                    'sender_id': sender.id,
                    'sender_avatar': avatar_url,
                    'message': message,
                    'post_id': post_id,
                    'unread_count': unread_count,
                }
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'WS group_send failed: {e}')

        # Trigger Native Push Notification (Firebase)
        try:
            from .utils import send_push_notification
            receiver_user = User.objects.get(id=receiver_id)
            send_push_notification(
                user=receiver_user,
                title="Aetheria",
                body=message,
                data={
                    'notification_type': notification_type, 
                    'post_id': str(post_id) if post_id else '',
                    'sender_id': str(sender.id)
                }
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Firebase push failed: {e}')

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Notification handler failed: {e}')
