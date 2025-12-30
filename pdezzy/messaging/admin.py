from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'agent', 'seller', 'conversation_type', 'is_active', 'created_at', 'last_message_at']
    list_filter = ['conversation_type', 'is_active', 'created_at']
    search_fields = ['agent__username', 'seller__username']
    readonly_fields = ['created_at', 'updated_at', 'last_message_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender_type', 'is_read', 'created_at']
    list_filter = ['sender_type', 'is_read', 'created_at']
    search_fields = ['conversation__id', 'content']
    readonly_fields = ['created_at', 'updated_at', 'read_at']
