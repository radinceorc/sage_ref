import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from sage_ref.models.room import Room
from sage_ref.models.chat import ChatMessage, Agent
from sage_ref.helpers.enums import AgentStatus

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.chatroom_name = self.scope['url_route']['kwargs']['chatroom_name']
        print(f"Chat room name: {self.chatroom_name}")
        self.room = get_object_or_404(Room, name=self.chatroom_name)
        self.room_group_name = f'chat_{self.chatroom_name}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            self.session_key = self.scope['session'].session_key
            self.set_client_status("online", is_authenticated=False)
        else:
            self.session_key = None
            self.set_client_status("online", is_authenticated=True)

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
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

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
        messages = list(ChatMessage.objects.filter(room=self.room).order_by('timestamp')[:50])
        first_message = messages[0]
        username =  first_message.author.username if first_message.author else "Anonymous",
        status = self.get_client_status()
        is_agent = str(self.room.agent) == str(self.scope['user'].username)
        context = {
            'chatroom_name': self.chatroom_name,
            'messages': messages,
            'user': self.scope['user'],
            'agent': self.room.agent,
            'room': self.room,
            'username':username[0],
            'status': status,
            'is_agent': is_agent
        }
        print(is_agent)
        
        html_message = render_to_string("chat.html", context)
        self.send(text_data=html_message)

    def send_agent_status_to_clients(self, disconnect=False):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'agent_status_update',
                'disconnect': disconnect,
            }
        )

    def agent_status_update(self, event):
        self.room = get_object_or_404(Room, name=self.chatroom_name)
        self.room.agent.status = AgentStatus.OFFLINE if event['disconnect'] else AgentStatus.ONLINE
        self.room.agent.save()
        context = {'agent': self.room.agent}
        html_message = render_to_string("agent_info.html", context)
        self.send(text_data=html_message)

    def set_client_status(self, status, is_authenticated):
        """
        Broadcast the client's online/offline status to the agent.
        """
        if is_authenticated:
            identifier = self.user.username
        else:
            identifier = self.session_key

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'client_status_update',
                'status': status,
                'identifier': identifier,
                'is_authenticated': is_authenticated
            }
        )

    def client_status_update(self, event):
        status = event['status']
        identifier = event['identifier']
        is_authenticated = event['is_authenticated']

        context = {
            'client_status': status,
            'identifier': identifier,
            'is_authenticated': is_authenticated
        }
        html_message = render_to_string("client_info.html", context)
        self.send(text_data=html_message)

    def get_client_status(self):
        if self.user.is_authenticated:
            return "online"
        return "online" if self.session_key else "offline"
