import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time messaging between agent and seller."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
            self.conversation_group_name = f'chat_{self.conversation_id}'
            
            # Get user from scope
            user = self.scope['user']
            
            # Check if user is authenticated
            if not user or user.is_anonymous:
                logger.warning(f"Anonymous user tried to connect to conversation {self.conversation_id}")
                await self.close(code=4001, reason="Unauthorized - No valid token")
                return
            
            logger.info(f"User {user.id} attempting to connect to conversation {self.conversation_id}")
            
            # Verify user has access to this conversation
            has_access = await self.verify_conversation_access(user, self.conversation_id)
            
            if not has_access:
                logger.warning(f"User {user.id} denied access to conversation {self.conversation_id}")
                await self.close(code=4003, reason="Forbidden - No access to this conversation")
                return
            
            # Join the conversation group
            await self.channel_layer.group_add(
                self.conversation_group_name,
                self.channel_name
            )
            
            logger.info(f"User {user.id} connected to conversation {self.conversation_id}")
            await self.accept()
            
            # Send all previous messages from this conversation
            previous_messages = await self.get_previous_messages(self.conversation_id)
            
            # Send each message to the connected user
            for message in previous_messages:
                await self.send(text_data=json.dumps({
                    'type': 'previous_message',
                    'message_id': message['id'],
                    'conversation_id': message['conversation_id'],
                    'sender_type': message['sender_type'],
                    'sender_name': message['sender_name'],
                    'sender_email': message['sender_email'],
                    'content': message['content'],
                    'created_at': message['created_at'],
                    'is_read': message['is_read'],
                }))
            
            logger.info(f"Sent {len(previous_messages)} previous messages to user {user.id}")
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close(code=4000, reason=f"Connection error: {str(e)}")

    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket."""
        try:
            data = json.loads(text_data)
            message_content = data.get('message', '').strip()
            
            if not message_content:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message cannot be empty'
                }))
                return
            
            # Save message to database
            user = self.scope['user']
            message = await self.save_message(
                self.conversation_id,
                message_content,
                user
            )
            
            if not message:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to save message'
                }))
                return
            
            # Broadcast message to group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'conversation_id': message['conversation_id'],
                    'sender_type': message['sender_type'],
                    'sender_name': message['sender_name'],
                    'sender_email': message['sender_email'],
                    'content': message['content'],
                    'created_at': message['created_at'],
                    'is_read': message['is_read'],
                }
            )
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """Receive message from group and send to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'conversation_id': event['conversation_id'],
            'sender_type': event['sender_type'],
            'sender_name': event['sender_name'],
            'sender_email': event['sender_email'],
            'content': event['content'],
            'created_at': event['created_at'],
            'is_read': event['is_read'],
        }))
    
    @database_sync_to_async
    def verify_conversation_access(self, user, conversation_id):
        """Verify that the user has access to this conversation."""
        from .models import Conversation
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            if isinstance(user, Agent):
                return conversation.agent_id == user.id
            elif isinstance(user, Seller):
                return conversation.seller_id == user.id
            elif isinstance(user, Buyer):
                return conversation.buyer_id == user.id
            
            return False
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_previous_messages(self, conversation_id, limit=50):
        """
        Get all previous messages from a conversation.
        Returns messages ordered from oldest to newest (for proper conversation flow).
        """
        from .models import Conversation, Message
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Get all messages ordered by created_at (oldest first)
            messages = Message.objects.filter(
                conversation=conversation
            ).order_by('created_at')[:limit]
            
            message_list = []
            for message in messages:
                if message.sender_type == 'agent':
                    sender_name = message.agent.get_full_name() or message.agent.username
                    sender_email = message.agent.email
                elif message.sender_type == 'seller':
                    sender_name = message.seller.get_full_name() or message.seller.username
                    sender_email = message.seller.email
                elif message.sender_type == 'buyer':
                    sender_name = message.buyer.get_full_name() or message.buyer.username
                    sender_email = message.buyer.email
                else:
                    sender_name = 'Unknown'
                    sender_email = ''
                
                message_list.append({
                    'id': message.id,
                    'conversation_id': message.conversation_id,
                    'sender_type': message.sender_type,
                    'sender_name': sender_name,
                    'sender_email': sender_email,
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                })
            
            return message_list
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error fetching previous messages: {e}")
            return []
    
    @database_sync_to_async
    def save_message(self, conversation_id, content, user):
        """Save message to database and return message data."""
        from .models import Conversation, Message
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            if isinstance(user, Agent):
                message = Message.objects.create(
                    conversation=conversation,
                    sender_type='agent',
                    agent=user,
                    content=content
                )
            elif isinstance(user, Seller):
                message = Message.objects.create(
                    conversation=conversation,
                    sender_type='seller',
                    seller=user,
                    content=content
                )
            elif isinstance(user, Buyer):
                message = Message.objects.create(
                    conversation=conversation,
                    sender_type='buyer',
                    buyer=user,
                    content=content
                )
            else:
                return None
            
            # Update conversation's last_message_at
            conversation.last_message_at = message.created_at
            conversation.save(update_fields=['last_message_at', 'updated_at'])
            
            # Prepare message data
            if message.sender_type == 'agent':
                sender_name = message.agent.get_full_name() or message.agent.username
                sender_email = message.agent.email
            elif message.sender_type == 'seller':
                sender_name = message.seller.get_full_name() or message.seller.username
                sender_email = message.seller.email
            elif message.sender_type == 'buyer':
                sender_name = message.buyer.get_full_name() or message.buyer.username
                sender_email = message.buyer.email
            else:
                sender_name = 'Unknown'
                sender_email = ''
            
            return {
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_type': message.sender_type,
                'sender_name': sender_name,
                'sender_email': sender_email,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read,
            }
        
        except Conversation.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
