from django.urls import re_path
from .LawChatBotConsumer import LawChatbotConsumer

websocket_urlpatterns = [
    re_path(r'ws/lawchatbot/$', LawChatbotConsumer.as_asgi()),
]
