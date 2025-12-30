from django.urls import re_path, path, include
from messaging.routing import websocket_urlpatterns as messaging_patterns

websocket_urlpatterns = messaging_patterns
