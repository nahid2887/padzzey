from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Conversations
    path('conversations/', views.ConversationListView.as_view(), name='conversation_list'),
    path('conversations/<int:id>/', views.ConversationDetailView.as_view(), name='conversation_detail'),
    
    # Messages
    path('conversations/<int:conversation_id>/messages/', views.MessageListView.as_view(), name='message_list'),
    path('conversations/<int:conversation_id>/mark-as-read/', views.mark_messages_as_read, name='mark_as_read'),
    
    # Clear & Delete Conversations
    path('conversations/<int:conversation_id>/clear/', views.clear_conversation, name='clear_conversation'),
    path('conversations/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    
    # Unread count
    path('unread-count/', views.get_unread_count, name='unread_count'),
]
