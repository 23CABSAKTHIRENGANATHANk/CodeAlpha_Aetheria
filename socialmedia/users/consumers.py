import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message, Notification
from channels.db import database_sync_to_async

import asyncio
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
            
        url_route_kwargs = self.scope['url_route']['kwargs']
        if 'room_id' in url_route_kwargs:
            self.room_id = url_route_kwargs['room_id']
        else:
            other_user_id = url_route_kwargs['user_id']
            self.room_id = await self.get_or_create_direct_room_async(self.user.id, int(other_user_id))
            
        self.room_group_name = f'chat_room_{self.room_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Mark messages read on connect
        seen_msg_ids = await self.mark_messages_read_in_room(self.room_id, self.user.id)
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
        
        # 1. Typing indicators
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
            
        # 2. Voice recording indicator
        if text_data_json.get('type') == 'recording_voice':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_recording_voice',
                    'sender_id': self.user.id,
                    'is_recording': text_data_json.get('is_recording', True)
                }
            )
            return

        # 3. Message reactions
        if text_data_json.get('type') == 'react':
            msg_id = text_data_json.get('message_id')
            reaction = text_data_json.get('reaction')
            status = await self.save_message_reaction(msg_id, self.user.id, reaction)
            if status:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_reaction',
                        'message_id': msg_id,
                        'sender_id': self.user.id,
                        'reaction': reaction
                    }
                )
            return

        # 4. Message deletion
        if text_data_json.get('type') == 'delete':
            msg_id = text_data_json.get('message_id')
            delete_type = text_data_json.get('delete_type')
            status = await self.delete_message_record(msg_id, self.user.id, delete_type)
            if status:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_delete',
                        'message_id': msg_id,
                        'delete_type': delete_type,
                        'sender_id': self.user.id
                    }
                )
            return

        # 4.1 Message Pinning
        if text_data_json.get('type') == 'pin':
            msg_id = text_data_json.get('message_id')
            is_pinned = text_data_json.get('is_pinned', False)
            status = await self.pin_message_record(msg_id, self.user.id, is_pinned)
            if status:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_pin',
                        'message_id': msg_id,
                        'is_pinned': is_pinned,
                        'sender_id': self.user.id
                    }
                )
            return

        # 4.2 WebRTC Calling Signaling
        if text_data_json.get('type') in ['call-offer', 'call-answer', 'ice-candidate', 'call-decline', 'call-hangup']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_call_signal',
                    'signal_data': text_data_json,
                    'sender_id': self.user.id
                }
            )
            return

        # 5. Text message sending
        message = text_data_json.get('message')
        parent_id = text_data_json.get('parent_id')
        is_forwarded = text_data_json.get('is_forwarded', False)
        if not message: return

        msg_id, initial_status = await self.create_and_save_message_in_room(
            self.user.id, self.room_id, message, parent_id, is_forwarded
        )

        time_str = timezone.now().isoformat()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': msg_id,
                'message': message,
                'sender_id': self.user.id,
                'time': time_str,
                'status': initial_status,
                'parent_id': parent_id,
                'is_forwarded': is_forwarded
            }
        )

        # Notify in the background
        asyncio.create_task(self.save_and_notify_background(message, msg_id))

    async def save_and_notify_background(self, message, message_id):
        try:
            avatar_url = self.user.profile.profile_image.url
        except Exception:
            avatar_url = '/static/images/default_profile.png'

        # Fetch room participants to push alerts
        members = await self.get_room_members_except_me(self.room_id, self.user.id)
        for member_id in members:
            unread_msg = await self.get_unread_messages_count(member_id)
            
            # Create Database Notification for Notification Center
            await self.create_db_notification(member_id)
            
            try:
                await self.channel_layer.group_send(
                    f'notif_{member_id}',
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
            await self.send_firebase_push(member_id, self.user, message)

    @database_sync_to_async
    def send_firebase_push(self, receiver_id, sender, body):
        try:
            from .utils import send_push_notification
            receiver_user = User.objects.get(id=receiver_id)
            unread_count = Message.objects.filter(receiver=receiver_user).exclude(status='seen').count()
            send_push_notification(
                user=receiver_user,
                title=f"New message from {sender.username}",
                body=body,
                data={'notification_type': 'message', 'sender_id': str(sender.id)},
                badge=unread_count
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Firebase push failed: {e}')
            
    @database_sync_to_async
    def create_db_notification(self, receiver_id):
        try:
            receiver_user = User.objects.get(id=receiver_id)
            Notification.objects.create(
                sender=self.user,
                receiver=receiver_user,
                notification_type='message'
            )
        except Exception as e:
            pass

    # Receive methods from Channel Layer Group
    async def chat_message(self, event):
        message_id = event.get('message_id')
        message = event['message']
        sender_id = event['sender_id']
        time = event['time']
        status = event.get('status', 'sent')
        parent_id = event.get('parent_id')
        is_forwarded = event.get('is_forwarded', False)
        file_url = event.get('file_url', '')
        file_type = event.get('file_type', 'text')
        file_name = event.get('file_name', '')

        if sender_id != self.user.id:
            await self.update_message_status(message_id, 'seen')
            status = 'seen'
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_seen',
                    'seen_by': self.user.id,
                    'message_ids': [message_id]
                }
            )

        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': message_id,
            'message': message,
            'sender_id': sender_id,
            'time': time,
            'status': status,
            'parent_id': parent_id,
            'is_forwarded': is_forwarded,
            'file_url': file_url,
            'file_type': file_type,
            'file_name': file_name
        }))
        
    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'is_typing': event['is_typing']
        }))

    async def chat_recording_voice(self, event):
        await self.send(text_data=json.dumps({
            'type': 'recording_voice',
            'sender_id': event['sender_id'],
            'is_recording': event['is_recording']
        }))

    async def chat_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'reaction': event['reaction']
        }))

    async def chat_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': event['message_id'],
            'delete_type': event['delete_type'],
            'sender_id': event['sender_id']
        }))

    async def chat_pin(self, event):
        await self.send(text_data=json.dumps({
            'type': 'pin',
            'message_id': event['message_id'],
            'is_pinned': event['is_pinned'],
            'sender_id': event['sender_id']
        }))

    async def chat_call_signal(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_signal',
            'signal_data': event['signal_data'],
            'sender_id': event['sender_id']
        }))

    async def messages_seen(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_seen',
            'seen_by': event['seen_by'],
            'message_ids': event['message_ids']
        }))

    @database_sync_to_async
    def get_or_create_direct_room_async(self, u1_id, u2_id):
        from .models import ChatRoom, GroupMember
        u1 = User.objects.get(id=u1_id)
        u2 = User.objects.get(id=u2_id)
        
        # Find direct room containing both
        rooms = ChatRoom.objects.filter(room_type='direct')
        for r in rooms:
            m_ids = list(r.members.values_list('user_id', flat=True))
            if len(m_ids) == 2 and u1.id in m_ids and u2.id in m_ids:
                return r.id
                
        # Create
        room = ChatRoom.objects.create(room_type='direct', title=f"{u1.username} & {u2.username}")
        GroupMember.objects.create(chat_room=room, user=u1, role='admin')
        GroupMember.objects.create(chat_room=room, user=u2, role='member')
        return room.id

    @database_sync_to_async
    def mark_messages_read_in_room(self, room_id, user_id):
        from .models import Message
        unread = Message.objects.filter(chat_room_id=room_id).exclude(sender_id=user_id).exclude(status='seen')
        m_ids = list(unread.values_list('id', flat=True))
        if m_ids:
            unread.update(is_read=True, status='seen')
        return m_ids

    @database_sync_to_async
    def create_and_save_message_in_room(self, sender_id, room_id, body, parent_id=None, is_forwarded=False):
        from .models import Message, ChatRoom
        sender = User.objects.get(id=sender_id)
        room = ChatRoom.objects.get(id=room_id)
        
        members = room.members.exclude(user_id=sender_id).select_related('user__profile')
        any_online = any(m.user.profile.is_online for m in members)
        initial_status = 'delivered' if any_online else 'sent'
        
        parent = None
        if parent_id:
            try:
                parent = Message.objects.get(id=parent_id)
            except Message.DoesNotExist:
                pass
                
        msg = Message.objects.create(
            sender=sender, chat_room=room, body=body, status=initial_status,
            is_read=(initial_status == 'seen'), parent_message=parent, is_forwarded=is_forwarded
        )
        return msg.id, initial_status

    @database_sync_to_async
    def update_message_status(self, message_id, status):
        from .models import Message
        try:
            msg = Message.objects.get(id=message_id)
            msg.status = status
            if status == 'seen':
                msg.is_read = True
            msg.save(update_fields=['status', 'is_read'])
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def save_message_reaction(self, message_id, user_id, reaction):
        from .models import Message, MessageReaction
        try:
            msg = Message.objects.get(id=message_id)
            user = User.objects.get(id=user_id)
            if not reaction:
                MessageReaction.objects.filter(message=msg, user=user).delete()
            else:
                MessageReaction.objects.update_or_create(
                    message=msg, user=user,
                    defaults={'reaction': reaction}
                )
            return True
        except Exception:
            return False

    @database_sync_to_async
    def delete_message_record(self, message_id, user_id, delete_type):
        from .models import Message
        try:
            msg = Message.objects.get(id=message_id)
            if delete_type == 'everyone':
                if msg.sender_id == user_id:
                    msg.is_deleted_everyone = True
                    msg.body = "This message was deleted"
                    msg.save(update_fields=['is_deleted_everyone', 'body'])
                    return True
            else: # 'me'
                user = User.objects.get(id=user_id)
                msg.deleted_by_users.add(user)
                return True
        except Exception:
            pass
        return False

    @database_sync_to_async
    def pin_message_record(self, message_id, user_id, is_pinned):
        from .models import Message
        try:
            msg = Message.objects.get(id=message_id)
            if msg.chat_room.members.filter(user_id=user_id).exists():
                msg.is_pinned = is_pinned
                msg.save(update_fields=['is_pinned'])
                return True
        except Exception:
            pass
        return False

    @database_sync_to_async
    def get_room_members_except_me(self, room_id, user_id):
        from .models import ChatRoom
        room = ChatRoom.objects.get(id=room_id)
        return list(room.members.exclude(user_id=user_id).values_list('user_id', flat=True))

    @database_sync_to_async
    def get_unread_messages_count(self, user_id):
        from .models import Message
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
                },
                badge=unread_count
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Firebase push failed: {e}')

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Notification handler failed: {e}')
