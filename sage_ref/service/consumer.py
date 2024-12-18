import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from asgiref.sync import sync_to_async
from django.shortcuts import get_object_or_404
from sage_ref.models.room import Room
from sage_ref.models.chat import ChatMessage
from sage_ref.helpers.enums import AgentStatus
from django.contrib.auth import get_user_model

User = get_user_model()

online_clients = {}


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        global online_clients
        self.chatroom_name = self.scope['url_route']['kwargs']['chatroom_name']
        print(f"Chat room name: {self.chatroom_name}")
        # breakpoint()
        # Use async ORM operations
        self.room = await sync_to_async(get_object_or_404)(Room, name=self.chatroom_name)
        self.room_group_name = f'chat_{self.chatroom_name}'
        self.user = self.scope['user']

        # Handle session key and online status
        if not self.user.is_authenticated:
            self.session_key = self.scope['session'].session_key
            identifier = self.session_key
            await self.set_client_status("online", is_authenticated=False)
        else:
            self.session_key = None
            identifier = self.user.username
            await self.set_client_status("online", is_authenticated=True)
        
        online_clients[identifier] = "online"

        # Add to group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Mark agent online if applicable
        user_has_agent = await sync_to_async(lambda user: hasattr(user, 'agent'))(self.user)
        if self.user.is_authenticated and user_has_agent:
            self.room.agent.status = AgentStatus.ONLINE
            await sync_to_async(self.room.agent.save)()
            await self.send_agent_status_to_clients()

        await self.accept()

    async def disconnect(self, close_code):
        global online_clients
        identifier = self.user.username if self.user.is_authenticated else self.session_key
        online_clients[identifier] = "offline"

        # Remove from group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if not self.user.is_authenticated:
            await self.set_client_status("offline", is_authenticated=False)
        elif self.user.is_authenticated:
            await self.set_client_status("offline", is_authenticated=True)
            if hasattr(self.user, 'agent'):
                self.room.agent.status = AgentStatus.OFFLINE
                await sync_to_async(self.room.agent.save)()
                await self.send_agent_status_to_clients(True)

    async def receive(self, text_data):
        print(f"Message received: {text_data}")
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')
        typing = text_data_json.get('typing', False)

        # Handle typing notification
        if typing:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'username': self.user.username if self.user.is_authenticated else "Anonymous",
                    'typing': typing,
                }
            )
            return

        # Handle message
        if message:
            if self.user.is_authenticated:
                chat_message = await sync_to_async(ChatMessage.objects.create)(
                    room=self.room,
                    author=self.user,
                    message=message
                )
            else:
                chat_message = await sync_to_async(ChatMessage.objects.create)(
                    room=self.room,
                    session_key=self.session_key,
                    message=message
                )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username if self.user.is_authenticated else "Anonymous",
                    'timestamp': chat_message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    async def chat_message(self, event):
        global online_clients
        messages = await sync_to_async(list)(
                ChatMessage.objects.filter(room=self.room).order_by('timestamp')[:50]
        )
        first_message = messages[0]

        if first_message.author_id:
            author_username = await sync_to_async(
                lambda: User.objects.filter(id=first_message.author_id).values_list(User.USERNAME_FIELD, flat=True).first()
            )()
        else:
            author_username = "Anonymous"

        agent_username = await sync_to_async(lambda: str(self.room.agent.user.username) if self.room.agent else None)()

            # Determine if the user is an agent
        is_agent = agent_username == await sync_to_async(lambda: str(self.scope['user'].username))()

        context = {
                'chatroom_name': self.chatroom_name,
                'messages': messages,
                'user': self.scope['user'],
                'agent': self.room.agent,
                'room': self.room,
                'username': author_username,
                'is_agent': is_agent,
                'client_status': online_clients.get(author_username),
            }
        html_message = render_to_string("chat.html", context)
        await self.send(text_data=html_message)


    async def user_typing(self, event):
        print(f"Typing event: {event}")
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'typing': event['typing'],
        }))

    async def send_agent_status_to_clients(self, disconnect=False):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'agent_status_update',
                'disconnect': disconnect,
            }
        )

    async def agent_status_update(self, event):
        self.room = await sync_to_async(get_object_or_404)(Room, name=self.chatroom_name)
        self.room.agent.status = AgentStatus.OFFLINE if event['disconnect'] else AgentStatus.ONLINE
        await sync_to_async(self.room.agent.save)()
        context = {'agent': self.room.agent}
        html_message = render_to_string("agent_info.html", context)
        await self.send(text_data=html_message)

    async def set_client_status(self, status, is_authenticated):
        if is_authenticated:
            identifier = self.user.username
        else:
            identifier = self.session_key

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'client_status_update',
                'status': status,
                'identifier': identifier,
                'is_authenticated': is_authenticated,
            }
        )

    async def client_status_update(self, event):
        status = event['status']
        identifier = event['identifier']
        is_authenticated = event['is_authenticated']

        context = {
            'client_status': status,
            'identifier': identifier,
            'is_authenticated': is_authenticated,
        }
        html_message = render_to_string("client_info.html", context)
        await self.send(text_data=html_message)
