import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from common.models import Conversation, Message, ConversationParticipant
from seller.models import Seller
from buyer.models import Buyer
from agent.models import Agent


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling real-time messaging"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user_id = None
        self.user_type = None
        self.user = None

        # Try to authenticate user from token
        await self.authenticate_user()

        if not self.user:
            await self.close()
            return

        # Check if user has access to this conversation
        has_access = await self.check_conversation_access()
        if not has_access:
            await self.close(code=4003)  # Forbidden
            return

        self.room_group_name = f'chat_{self.conversation_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send message history to the connecting user
        await self.send_message_history()

        # Mark messages as read
        await self.mark_messages_as_read()

        # Send connection status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user_id,
                'user_type': self.user_type,
                'status': 'online',
                'timestamp': timezone.now().isoformat(),
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            # Send disconnection status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user_id,
                    'user_type': self.user_type,
                    'status': 'offline',
                    'timestamp': timezone.now().isoformat(),
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def send_message_history(self):
        """Send conversation message history to the connecting user"""
        messages = await self.get_conversation_messages()
        
        # Send history messages (oldest first)
        for message in messages:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message_id': message.id,
                'sender_id': message.sender_id,
                'sender_type': message.sender_type,
                'sender_name': self.get_sender_name(message),
                'content': message.content,
                'message_type': message.message_type,
                'file_url': message.file_url or '',
                'is_read': message.is_read,
                'created_at': message.created_at.isoformat(),
                'timestamp': message.created_at.isoformat(),
            }))

    @database_sync_to_async
    def get_conversation_messages(self):
        """Get all messages for this conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            # Get messages ordered by created_at (oldest first for history)
            messages = conversation.messages.all().order_by('created_at')
            return list(messages)
        except Conversation.DoesNotExist:
            return []

    def get_sender_name(self, message):
        """Get sender's full name"""
        if message.sender_type == 'seller':
            try:
                seller = Seller.objects.get(id=message.sender_id)
                return seller.get_full_name() or seller.username
            except Seller.DoesNotExist:
                return 'Unknown Seller'
        elif message.sender_type == 'buyer':
            try:
                buyer = Buyer.objects.get(id=message.sender_id)
                return buyer.get_full_name() or buyer.username
            except Buyer.DoesNotExist:
                return 'Unknown Buyer'
        elif message.sender_type == 'agent':
            try:
                agent = Agent.objects.get(id=message.sender_id)
                return agent.get_full_name() or agent.username
            except Agent.DoesNotExist:
                return 'Unknown Agent'
        return 'Unknown User'

    async def receive(self, text_data):
        """Handle incoming messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_message(self, data):
        """Handle incoming chat message"""
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        file_url = data.get('file_url', '')

        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content cannot be empty'
            }))
            return

        # Save message to database
        message = await self.save_message(content, message_type, file_url)

        if message:
            # Broadcast message to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'sender_id': self.user_id,
                    'sender_type': self.user_type,
                    'sender_name': message.get('sender_name', ''),
                    'content': content,
                    'message_type': message_type,
                    'file_url': file_url,
                    'created_at': message.get('created_at', ''),
                    'timestamp': timezone.now().isoformat(),
                }
            )

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user_id,
                'user_type': self.user_type,
                'is_typing': is_typing,
                'timestamp': timezone.now().isoformat(),
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt for message"""
        message_id = data.get('message_id')
        
        if message_id:
            await self.mark_message_as_read(message_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': self.user_id,
                    'user_type': self.user_type,
                    'timestamp': timezone.now().isoformat(),
                }
            )

    # WebSocket event handlers

    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_type': event['sender_type'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'message_type': event['message_type'],
            'file_url': event.get('file_url', ''),
            'created_at': event['created_at'],
            'timestamp': event['timestamp'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_type': event['user_type'],
            'is_typing': event['is_typing'],
            'timestamp': event['timestamp'],
        }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'user_type': event['user_type'],
            'timestamp': event['timestamp'],
        }))

    async def user_status(self, event):
        """Send user status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'user_id': event['user_id'],
            'user_type': event['user_type'],
            'status': event['status'],
            'timestamp': event['timestamp'],
        }))

    # Database operations

    @database_sync_to_async
    def authenticate_user(self):
        """Authenticate user from JWT token"""
        token = None
        
        # Get token from query parameters
        if 'token' in self.scope['query_string'].decode().split('&'):
            for param in self.scope['query_string'].decode().split('&'):
                if param.startswith('token='):
                    token = param.split('=', 1)[1]
                    break

        if not token:
            return False

        try:
            from rest_framework_simplejwt.tokens import UnicodeJWTToken
            decoded_token = UnicodeJWTToken(token)
            user_id = decoded_token['user_id']
            user_type = decoded_token.get('user_type', 'seller')

            # Get user from database
            if user_type == 'seller':
                user = Seller.objects.get(id=user_id)
            elif user_type == 'buyer':
                user = Buyer.objects.get(id=user_id)
            elif user_type == 'agent':
                user = Agent.objects.get(id=user_id)
            else:
                return False

            self.user_id = user_id
            self.user_type = user_type
            self.user = user
            return True
        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    @database_sync_to_async
    def check_conversation_access(self):
        """Check if user has access to this conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Check if user is part of this conversation
            if self.user_type == 'seller' and conversation.seller_id == self.user_id:
                return True
            elif self.user_type in ['buyer', 'agent']:
                if (conversation.other_user_id == self.user_id and 
                    conversation.other_user_type == self.user_type):
                    return True
            
            return False
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, message_type, file_url):
        """Save message to database"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            message = Message.objects.create(
                conversation=conversation,
                sender_id=self.user_id,
                sender_type=self.user_type,
                message_type=message_type,
                content=content,
                file_url=file_url if file_url else None,
            )

            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()

            # Update unread count for other participant
            self.update_unread_count(conversation)

            return {
                'id': message.id,
                'sender_name': self.user.get_full_name() or self.user.username,
                'created_at': message.created_at.isoformat(),
            }
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    def update_unread_count(self, conversation):
        """Update unread count for other participant"""
        try:
            participant = ConversationParticipant.objects.get(
                conversation=conversation,
                user_id=conversation.other_user_id,
                user_type=conversation.other_user_type
            )
            participant.unread_count += 1
            participant.save()
        except ConversationParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_messages_as_read(self):
        """Mark all messages in conversation as read for current user"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Mark messages as read
            Message.objects.filter(
                conversation=conversation
            ).exclude(
                sender_id=self.user_id,
                sender_type=self.user_type
            ).update(is_read=True)

            # Update participant
            participant, created = ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user_id=self.user_id,
                user_type=self.user_type
            )
            participant.unread_count = 0
            participant.last_read_at = timezone.now()
            participant.save()
        except Exception as e:
            print(f"Error marking messages as read: {e}")

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark specific message as read"""
        try:
            message = Message.objects.get(id=message_id)
            message.is_read = True
            message.save()
        except Message.DoesNotExist:
            pass
