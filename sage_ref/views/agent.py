from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.db.models import Count
from sage_ref.models import Room, ChatMessage,Agent
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

@method_decorator(login_required, name='dispatch')
class AgentChatPanelView(TemplateView):
    template_name = 'agent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rooms'] = Room.objects.annotate(message_count=Count('messages')).filter(message_count__gt=0)
        context['messages'] = ChatMessage.objects.all().order_by('timestamp')[:50]
        return context


class AgentChatRoomView(TemplateView):
    template_name = 'chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        chatroom_name = self.kwargs['chatroom_name']
        room = get_object_or_404(Room, name=chatroom_name)
        agent = get_object_or_404(Agent, user=self.request.user)
        room.agent = agent
        room.save()
        is_agent = str(room.agent) == str(self.request.user)
        print(is_agent)
        context['is_agent'] = is_agent
        context['chatroom'] = room
        context['messages'] = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]
        context['rooms'] = Room.objects.all()
        return context