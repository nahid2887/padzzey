from django.db import models
from django.utils import timezone
from seller.models import Seller
from agent.models import Agent
from buyer.models import Buyer


class Conversation(models.Model):
    """
    Represents a conversation between:
    - Agent and Seller (for selling requests)
    - Agent and Buyer (for property showings/inquiries)
    """
    CONVERSATION_TYPES = [
        ('selling_request', 'Selling Request Discussion'),
        ('showing_inquiry', 'Property Showing Inquiry'),
        ('general', 'General Discussion'),
    ]
    
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='conversations_as_agent')
    
    # Either seller or buyer (one will be set)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, null=True, blank=True, related_name='conversations_as_seller')
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=True, blank=True, related_name='conversations_as_buyer')
    
    conversation_type = models.CharField(max_length=20, choices=CONVERSATION_TYPES, default='general')
    
    # Optional references
    selling_request = models.ForeignKey(
        'seller.SellingRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    showing_schedule = models.ForeignKey(
        'buyer.ShowingSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    property_listing = models.ForeignKey(
        'agent.PropertyListing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    
    subject = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['agent', 'seller']),
            models.Index(fields=['agent', 'buyer']),
            models.Index(fields=['-last_message_at']),
        ]
    
    def __str__(self):
        if self.seller:
            return f"Conversation: {self.agent.username} <-> {self.seller.username}"
        elif self.buyer:
            return f"Conversation: {self.agent.username} <-> {self.buyer.username}"
        return f"Conversation: {self.agent.username}"


class Message(models.Model):
    """
    Represents a single message in a conversation.
    Sender can be agent, seller, or buyer.
    """
    SENDER_TYPES = [
        ('agent', 'Agent'),
        ('seller', 'Seller'),
        ('buyer', 'Buyer'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # Sender type and ID
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages_as_agent')
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages_as_seller')
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages_as_buyer')
    
    content = models.TextField()
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        if self.sender_type == 'agent':
            sender = self.agent
        elif self.sender_type == 'seller':
            sender = self.seller
        else:
            sender = self.buyer
        return f"Message from {sender.username} - {self.created_at}"
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
