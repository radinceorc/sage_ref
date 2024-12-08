from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from sage_ref.helpers.enums import AgentStatus

User = get_user_model()

class Agent(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="agent",
        verbose_name=_("User"),
        help_text=_("The user associated with this agent."),
        db_comment="Reference to the user who acts as an agent."
    )
    status = models.CharField(
        max_length=10,
        choices=AgentStatus.choices,
        default=AgentStatus.OFFLINE,
        verbose_name=_("Status"),
        help_text=_("The current status of the agent."),
        db_comment="Tracks the agent's current status: Online, Offline, or Busy."
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Joined At"),
        help_text=_("The date and time the agent joined."),
        db_comment="The timestamp when the agent joined the chat support system."
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        help_text="Upload an avatar for the agent. This will be displayed in the chat interface.",
        db_comment="Stores the avatar image for the agent."
    )
    

    class Meta:
        verbose_name = _("Sage_Agent")
        verbose_name_plural = _("Sage_Agents")

    def __str__(self):
        return self.user.username

    def __repr__(self):
        return f"<Sage_Agent(user={self.user.username}, status={self.status}, joined_at={self.joined_at})>"
