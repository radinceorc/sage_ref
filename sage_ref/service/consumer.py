import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from sage_ref.models.room import Room
from sage_ref.models.chat import ChatMessage
from sage_ref.helpers.enums import AgentStatus
from django.contrib.auth import get_user_model

User = get_user_model()

online_clients = {}


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        global online_clients
        self.chatroom_name = self.scope['url_route']['kwargs']['chatroom_name']
        print(f"Chat room name: {self.chatroom_name}")
        self.room = get_object_or_404(Room, name=self.chatroom_name)
        self.room_group_name = f'chat_{self.chatroom_name}'
        self.user = self.scope['user']

        # Identify the user or session for tracking online status
        if not self.user.is_authenticated:
            self.session_key = self.scope['session'].session_key
            identifier = self.session_key
            self.set_client_status("online", is_authenticated=False)
        else:
            self.session_key = None
            identifier = self.user.username
            self.set_client_status("online", is_authenticated=True)

        online_clients[identifier] = "online"

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        # Mark agent online if applicable
        if self.user.is_authenticated and hasattr(self.user, 'agent'):
            self.room.agent.status = AgentStatus.ONLINE
            self.room.agent.save()
            self.send_agent_status_to_clients()

        self.accept()

    def disconnect(self, close_code):
        global online_clients
        identifier = self.user.username if self.user.is_authenticated else self.session_key
        online_clients[identifier] = "offline"

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

        if not self.user.is_authenticated:
            self.set_client_status("offline", is_authenticated=False)
        elif self.user.is_authenticated:
            self.set_client_status("offline", is_authenticated=True)
            if hasattr(self.user, 'agent'):
                self.room.agent.status = AgentStatus.OFFLINE
                self.room.agent.save()
                self.send_agent_status_to_clients(True)

    def receive(self, text_data):
        print(f"Message received: {text_data}")
        text_data_json = json.loads(text_data)

        # Separate handling for typing and actual message
        typing = text_data_json.get('typing', None)
        message = text_data_json.get('message', '')

        if typing is not None:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'username': self.user.username if self.user.is_authenticated else "Anonymous",
                    'typing': typing,
                }
            )
            return 

        if message:
            if self.user.is_authenticated:
                chat_message = ChatMessage.objects.create(
                    room=self.room,
                    author=self.user,
                    message=message
                )
            else:
                chat_message = ChatMessage.objects.create(
                    room=self.room,
                    session_key=self.session_key,
                    message=message
                )

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username if self.user.is_authenticated else "Anonymous",
                    'timestamp': chat_message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    def chat_message(self, event):
        global online_clients
        messages = list(ChatMessage.objects.filter(room=self.room).order_by('timestamp')[:50])
        first_message = messages[0]
        username = getattr(first_message.author, User.USERNAME_FIELD, "Anonymous") if first_message.author else "Anonymous"
        is_agent = str(self.room.agent) == str(self.scope['user'].username)
        context = {
            'chatroom_name': self.chatroom_name,
            'messages': messages,
            'user': self.scope['user'],
            'agent': self.room.agent,
            'room': self.room,
            'username': username,
            'is_agent': is_agent,
            'client_status': online_clients.get(first_message.author.username),
        }
        html_message = render_to_string("chat.html", context)
        self.send(text_data=html_message)

    def user_typing(self, event):
        print(f"Typing event: {event}")
        typing = False
        if event['typing'] == True:
            typing = True
        html_message = render_to_string("typing.html", {'typing': typing})
        self.send(text_data=html_message)

    def send_agent_status_to_clients(self, disconnect=False):
        # Broadcast agent status to all clients
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'agent_status_update',
                'disconnect': disconnect,
            }
        )

    def agent_status_update(self, event):
        # Broadcast agent status update
        self.room = get_object_or_404(Room, name=self.chatroom_name)
        self.room.agent.status = AgentStatus.OFFLINE if event['disconnect'] else AgentStatus.ONLINE
        self.room.agent.save()
        context = {'agent': self.room.agent}
        html_message = render_to_string("agent_info.html", context)
        self.send(text_data=html_message)

    def set_client_status(self, status, is_authenticated):
        identifier = self.user.username if is_authenticated else self.session_key
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'client_status_update',
                'status': status,
                'identifier': identifier,
                'is_authenticated': is_authenticated,
            }
        )

    def client_status_update(self, event):
        # Broadcast client status update
        context = {
            'client_status': event['status'],
            'identifier': event['identifier'],
            'is_authenticated': event['is_authenticated'],
        }
        html_message = render_to_string("client_info.html", context)
        self.send(text_data=html_message)
