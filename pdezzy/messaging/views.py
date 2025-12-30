from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)
from agent.models import Agent
from seller.models import Seller
from buyer.models import Buyer


class ConversationListView(generics.ListCreateAPIView):
    """
    List conversations for the current user (agent or seller).
    Users can only see conversations they're part of.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if isinstance(user, Agent):
            # Agent viewing conversations with sellers and buyers
            return Conversation.objects.filter(agent=user)
        elif isinstance(user, Seller):
            # Seller viewing their conversations with agents
            return Conversation.objects.filter(seller=user)
        elif isinstance(user, Buyer):
            # Buyer viewing their conversations with agents
            return Conversation.objects.filter(buyer=user)
        
        return Conversation.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new conversation.
        Required fields: other_user_id
        Optional: conversation_type, subject
        """
        user = request.user
        other_user_id = request.data.get('other_user_id')
        conversation_type = request.data.get('conversation_type', 'general')
        subject = request.data.get('subject', '')
        
        if not other_user_id:
            return Response(
                {'error': 'other_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if isinstance(user, Agent):
                # Agent creating conversation with seller or buyer
                try:
                    seller = Seller.objects.get(id=other_user_id)
                    conversation, created = Conversation.objects.get_or_create(
                        agent=user,
                        seller=seller,
                        defaults={
                            'conversation_type': conversation_type,
                            'subject': subject,
                        }
                    )
                except Seller.DoesNotExist:
                    buyer = Buyer.objects.get(id=other_user_id)
                    conversation, created = Conversation.objects.get_or_create(
                        agent=user,
                        buyer=buyer,
                        defaults={
                            'conversation_type': conversation_type,
                            'subject': subject,
                        }
                    )
            elif isinstance(user, Seller):
                # Seller creating conversation with agent
                agent = Agent.objects.get(id=other_user_id)
                conversation, created = Conversation.objects.get_or_create(
                    agent=agent,
                    seller=user,
                    defaults={
                        'conversation_type': conversation_type,
                        'subject': subject,
                    }
                )
            elif isinstance(user, Buyer):
                # Buyer creating conversation with agent
                agent = Agent.objects.get(id=other_user_id)
                conversation, created = Conversation.objects.get_or_create(
                    agent=agent,
                    buyer=user,
                    defaults={
                        'conversation_type': conversation_type,
                        'subject': subject,
                    }
                )
            else:
                return Response(
                    {'error': 'Invalid user type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ConversationListSerializer(
                conversation,
                context={'request': request}
            )
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        
        except (Agent.DoesNotExist, Seller.DoesNotExist, Buyer.DoesNotExist):
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ConversationDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a specific conversation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationDetailSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        
        if isinstance(user, Agent):
            return Conversation.objects.filter(agent=user)
        elif isinstance(user, Seller):
            return Conversation.objects.filter(seller=user)
        elif isinstance(user, Buyer):
            return Conversation.objects.filter(buyer=user)
        
        return Conversation.objects.none()
    
    def perform_update(self, serializer):
        # Only allow updating is_active status
        serializer.save(subject=serializer.instance.subject)


class MessageListView(generics.ListCreateAPIView):
    """
    List all messages in a conversation or create a new message.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        user = self.request.user
        
        # Verify user has access to this conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if isinstance(user, Agent):
            if conversation.agent_id != user.id:
                return Message.objects.none()
        elif isinstance(user, Seller):
            if conversation.seller_id != user.id:
                return Message.objects.none()
        elif isinstance(user, Buyer):
            if conversation.buyer_id != user.id:
                return Message.objects.none()
        else:
            return Message.objects.none()
        
        # Mark messages as read
        unread_messages = conversation.messages.filter(is_read=False)
        
        if isinstance(user, Agent):
            unread_messages = unread_messages.exclude(sender_type='agent')
        elif isinstance(user, Seller):
            unread_messages = unread_messages.exclude(sender_type='seller')
        elif isinstance(user, Buyer):
            unread_messages = unread_messages.exclude(sender_type='buyer')
        
        unread_messages.update(is_read=True, read_at=timezone.now())
        
        return conversation.messages.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_id')
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        user = self.request.user
        
        # Verify user has access to this conversation
        if isinstance(user, Agent):
            if conversation.agent_id != user.id:
                raise PermissionError("You don't have access to this conversation")
        elif isinstance(user, Seller):
            if conversation.seller_id != user.id:
                raise PermissionError("You don't have access to this conversation")
        elif isinstance(user, Buyer):
            if conversation.buyer_id != user.id:
                raise PermissionError("You don't have access to this conversation")
        
        serializer.save(conversation=conversation)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mark_messages_as_read(request, conversation_id):
    """
    Mark all unread messages in a conversation as read.
    """
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Verify access
    if isinstance(user, Agent):
        if conversation.agent_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        unread_messages = conversation.messages.filter(is_read=False).exclude(sender_type='agent')
    elif isinstance(user, Seller):
        if conversation.seller_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        unread_messages = conversation.messages.filter(is_read=False).exclude(sender_type='seller')
    else:
        return Response(
            {'error': 'Invalid user type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from django.utils import timezone
    count = unread_messages.update(is_read=True, read_at=timezone.now())
    
    return Response({
        'success': True,
        'marked_as_read': count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """
    Get total count of unread messages for the current user.
    """
    user = request.user
    
    if isinstance(user, Agent):
        unread_count = Message.objects.filter(
            conversation__agent=user,
            is_read=False
        ).exclude(sender_type='agent').count()
    elif isinstance(user, Seller):
        unread_count = Message.objects.filter(
            conversation__seller=user,
            is_read=False
        ).exclude(sender_type='seller').count()
    else:
        unread_count = 0
    
    return Response({'unread_count': unread_count})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_conversation(request, conversation_id):
    """
    Clear all messages from a conversation (soft delete).
    The conversation itself will be marked as inactive but not deleted.
    """
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Verify access
    if isinstance(user, Agent):
        if conversation.agent_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif isinstance(user, Seller):
        if conversation.seller_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Invalid user type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Delete all messages in the conversation
    message_count = conversation.messages.count()
    conversation.messages.all().delete()
    
    # Mark conversation as inactive
    conversation.is_active = False
    conversation.last_message_at = None
    conversation.save()
    
    return Response({
        'success': True,
        'message': 'Conversation cleared successfully',
        'messages_deleted': message_count,
        'conversation_id': conversation.id
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_conversation(request, conversation_id):
    """
    Permanently delete a conversation and all its messages.
    """
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Verify access
    if isinstance(user, Agent):
        if conversation.agent_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif isinstance(user, Seller):
        if conversation.seller_id != user.id:
            return Response(
                {'error': 'You don\'t have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Invalid user type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    conversation_data = {
        'id': conversation.id,
        'agent_id': conversation.agent_id,
        'seller_id': conversation.seller_id,
        'subject': conversation.subject,
        'message_count': conversation.messages.count()
    }
    
    # Delete the conversation (will cascade delete messages)
    conversation.delete()
    
    return Response({
        'success': True,
        'message': 'Conversation permanently deleted',
        'deleted_conversation': conversation_data
    }, status=status.HTTP_200_OK)