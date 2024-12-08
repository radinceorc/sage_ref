from django.utils.translation import gettext_lazy as _
from django.contrib import admin

from sage_ref.models import ChatMessage,Agent


admin.site.register(ChatMessage)

admin.site.register(Agent)

