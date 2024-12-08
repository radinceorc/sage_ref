from django.views.generic import TemplateView
from sage_ref.models import ChatMessage,Room

class ChatRoomView(TemplateView):
    template_name = 'chat.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            chatroom_name = user.username
        else:
            if not self.request.session.session_key:
                self.request.session.save() 
            chatroom_name = self.request.session.session_key
        room, created = Room.objects.get_or_create(name=chatroom_name)
        context['messages'] = ChatMessage.objects.filter(room=room).order_by('timestamp'        )[:50]
        context['chatroom_name'] = room.name
        return context
