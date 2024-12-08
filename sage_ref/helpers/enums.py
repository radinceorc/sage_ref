from django.db import models
from django.utils.translation import gettext_lazy as _

class AgentStatus(models.TextChoices):
    ONLINE = 'online', _("Online")
    OFFLINE = 'offline', _("Offline")
    BUSY = 'busy', _("Busy")
