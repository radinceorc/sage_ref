# chat/routing.py
from django.urls import path
from sage_ref.service.consumer import ChatConsumer

websocket_urlpatterns = [
    path("ws/chatroom/<str:chatroom_name>/", ChatConsumer.as_asgi()),

]
