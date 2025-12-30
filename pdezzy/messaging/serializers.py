from rest_framework import serializers
from .models import Conversation, Message
from agent.serializers import UserSerializer as AgentSerializer
from seller.serializers import UserSerializer as SellerSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender_type',
            'agent',
            'seller',
            'buyer',
            'sender_name',
            'sender_email',
            'content',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at', 'is_read']
    
    def get_sender_name(self, obj):
        if obj.sender_type == 'agent':
            return obj.agent.get_full_name() or obj.agent.username
        elif obj.sender_type == 'seller':
            if obj.seller:
                return obj.seller.get_full_name() or obj.seller.username
        elif obj.sender_type == 'buyer':
            if obj.buyer:
                return obj.buyer.get_full_name() or obj.buyer.username
        return 'Unknown'
    
    def get_sender_email(self, obj):
        if obj.sender_type == 'agent':
            return obj.agent.email
        elif obj.sender_type == 'seller':
            if obj.seller:
                return obj.seller.email
        elif obj.sender_type == 'buyer':
            if obj.buyer:
                return obj.buyer.email
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations."""
    agent_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    buyer_name = serializers.SerializerMethodField()
    agent_email = serializers.SerializerMethodField()
    seller_email = serializers.SerializerMethodField()
    buyer_email = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        ref_name = 'MessagingConversationListSerializer'
        fields = [
            'id',
            'agent',
            'agent_name',
            'agent_email',
            'seller',
            'seller_name',
            'seller_email',
            'buyer',
            'buyer_name',
            'buyer_email',
            'conversation_type',
            'selling_request',
            'subject',
            'is_active',
            'created_at',
            'updated_at',
            'last_message_at',
            'last_message',
            'unread_count',
            'other_user',
        ]
        read_only_fields = fields
    
    def get_agent_name(self, obj):
        if obj.agent:
            return obj.agent.get_full_name() or obj.agent.username
        return None
    
    def get_seller_name(self, obj):
        if obj.seller:
            return obj.seller.get_full_name() or obj.seller.username
        return None
    
    def get_buyer_name(self, obj):
        if obj.buyer:
            return obj.buyer.get_full_name() or obj.buyer.username
        return None
    
    def get_agent_email(self, obj):
        if obj.agent:
            return obj.agent.email
        return None
    
    def get_seller_email(self, obj):
        if obj.seller:
            return obj.seller.email
        return None
    
    def get_buyer_email(self, obj):
        if obj.buyer:
            return obj.buyer.email
        return None
    
    def get_last_message(self, obj):
        last_msg = obj.messages.first()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content,
                'sender_type': last_msg.sender_type,
                'created_at': last_msg.created_at,
                'is_read': last_msg.is_read,
            }
        return None
    
    def get_unread_count(self, obj):
        # Count unread messages for the current user
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        
        request = self.context.get('request')
        if not request:
            return 0
        
        unread_count = obj.messages.filter(is_read=False)
        
        # If request user is agent, count messages not from agent
        if isinstance(request.user, Agent):
            unread_count = unread_count.exclude(sender_type='agent')
        # If request user is seller, count messages not from seller
        elif isinstance(request.user, Seller):
            unread_count = unread_count.exclude(sender_type='seller')
        # If request user is buyer, count messages not from buyer
        elif isinstance(request.user, Buyer):
            unread_count = unread_count.exclude(sender_type='buyer')
        
        return unread_count.count()
    
    def get_other_user(self, obj):
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        
        request = self.context.get('request')
        if not request:
            return None
        
        # Determine if current user is agent, seller, or buyer
        if isinstance(request.user, Agent):
            # Current user is agent, return seller OR buyer info
            if obj.seller:
                profile_image_url = None
                if hasattr(obj.seller, 'profile_image') and obj.seller.profile_image:
                    profile_image_url = request.build_absolute_uri(obj.seller.profile_image.url)
                
                return {
                    'id': obj.seller.id,
                    'username': obj.seller.username,
                    'email': obj.seller.email,
                    'name': obj.seller.get_full_name() or obj.seller.username,
                    'type': 'seller',
                    'profile_image_url': profile_image_url,
                }
            elif obj.buyer:
                profile_image_url = None
                if hasattr(obj.buyer, 'profile_image') and obj.buyer.profile_image:
                    profile_image_url = request.build_absolute_uri(obj.buyer.profile_image.url)
                
                return {
                    'id': obj.buyer.id,
                    'username': obj.buyer.username,
                    'email': obj.buyer.email,
                    'name': obj.buyer.get_full_name() or obj.buyer.username,
                    'type': 'buyer',
                    'profile_image_url': profile_image_url,
                }
        elif isinstance(request.user, Seller):
            # Current user is seller, return agent info
            profile_image_url = None
            # Agent uses 'profile_picture' field
            if hasattr(obj.agent, 'profile_picture') and obj.agent.profile_picture:
                profile_image_url = request.build_absolute_uri(obj.agent.profile_picture.url)
            
            return {
                'id': obj.agent.id,
                'username': obj.agent.username,
                'email': obj.agent.email,
                'name': obj.agent.get_full_name() or obj.agent.username,
                'type': 'agent',
                'profile_image_url': profile_image_url,
            }
        elif isinstance(request.user, Buyer):
            # Current user is buyer, return agent info
            profile_image_url = None
            # Agent uses 'profile_picture' field
            if hasattr(obj.agent, 'profile_picture') and obj.agent.profile_picture:
                profile_image_url = request.build_absolute_uri(obj.agent.profile_picture.url)
            
            return {
                'id': obj.agent.id,
                'username': obj.agent.username,
                'email': obj.agent.email,
                'name': obj.agent.get_full_name() or obj.agent.username,
                'type': 'agent',
                'profile_image_url': profile_image_url,
            }
        
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with messages."""
    agent_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'agent',
            'agent_name',
            'seller',
            'seller_name',
            'conversation_type',
            'selling_request',
            'subject',
            'is_active',
            'created_at',
            'updated_at',
            'last_message_at',
            'messages',
        ]
        read_only_fields = fields
    
    def get_agent_name(self, obj):
        if obj.agent:
            return obj.agent.get_full_name() or obj.agent.username
        return None
    
    def get_seller_name(self, obj):
        if obj.seller:
            return obj.seller.get_full_name() or obj.seller.username
        return None


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""
    
    class Meta:
        model = Message
        fields = ['conversation', 'content']
    
    def create(self, validated_data):
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        
        request = self.context.get('request')
        conversation = validated_data['conversation']
        
        # Determine sender type and set appropriate sender
        if isinstance(request.user, Agent):
            message = Message.objects.create(
                sender_type='agent',
                agent=request.user,
                **validated_data
            )
        elif isinstance(request.user, Seller):
            message = Message.objects.create(
                sender_type='seller',
                seller=request.user,
                **validated_data
            )
        elif isinstance(request.user, Buyer):
            message = Message.objects.create(
                sender_type='buyer',
                buyer=request.user,
                **validated_data
            )
        
        # Update conversation's last_message_at
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=['last_message_at', 'updated_at'])
        
        return message
