import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # Create a unique room name for these two users
        # Sort IDs to ensure the room name is the same regardless of who connects
        ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_group_name = f'chat_{ids[0]}_{ids[1]}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Mark messages as read on connect
        await self.mark_messages_read(self.other_user_id, self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save message to database
        msg_obj = await self.save_message(self.user.id, self.other_user_id, message)

        time_str = msg_obj.created_at.strftime('%H:%M')
        
        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': self.user.id,
                'time': time_str,
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

        # Send message to WebSocket client
        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'time': time,
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
