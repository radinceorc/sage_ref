# chat/urls.py
from django.urls import path
from .views import (
    ChatRoomView,
    AgentChatPanelView,
    AgentChatRoomView
)

urlpatterns = [
    path('home/', ChatRoomView.as_view(), name='chat_room'),
    path('agent/',AgentChatPanelView.as_view(), name='agent_chat_panel'),
    path
    (
        'agent/<str:chatroom_name>/', 
        AgentChatRoomView.as_view(), name='chatroom'
    ),

]