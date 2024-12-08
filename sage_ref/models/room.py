from django.db import models
from django.utils.translation import gettext_lazy as _

class Room(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Room Name"),
        help_text=_("The name of the chat room."),
        db_comment="The name assigned to this chat room."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("The date and time the room was created."),
        db_comment="The timestamp of when this room was created."
    )
    agent = models.ForeignKey(
        "Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_room",
        verbose_name=_("Agent"),
        help_text=_("The agent who come to this room."),
        db_comment="References the agent who come to this room."
    )

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Room(name={self.name}, created_at={self.created_at})>"
