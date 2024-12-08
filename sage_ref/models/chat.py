from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from sage_ref.models.room import Room
from sage_ref.models.agent import Agent

User = get_user_model()

class ChatMessage(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Room"),
        help_text=_("The room where this message was sent."),
        db_comment="References the chat room this message belongs to."
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name=_("Agent"),
        help_text=_("The agent who sent this message."),
        db_comment="References the agent who sent this message."
    )
    author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Author"),
        related_name="user_chat",
        help_text=_("The user who sent this message."),
        db_comment="Reference to the user who created this message"
    )
    message = models.TextField(
        verbose_name=_("Message"),
        help_text=_("The content of the chat message."),
        db_comment="The actual text content of the message sent in the chat."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Timestamp"),
        help_text=_("The time this message was sent."),
        db_comment="The date and time when this message was created."
    )
    session_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Session Key"),
        help_text=_("Session key for anonymous users."),
        db_comment="The session key of the anonymous user (if not authenticated)."
    )

    class Meta:
        verbose_name = _("Chat Message")
        verbose_name_plural = _("Chat Messages")

    def __str__(self):
        return f"Message by {self.agent} in Room {self.room} at {self.timestamp}"

    def __repr__(self):
        return f"<ChatMessage(room={self.room}, agent={self.agent}, timestamp={self.timestamp})>"

    def clean(self):
        """
        Custom validation to ensure that either 'author' or 'session_key' is set, but not both.
        """
        if self.author and self.session_key:
            raise ValidationError(
                _('Both author and session_key cannot be set at the same time.'),
                code='invalid_author_session_key'
            )
        if not self.author and not self.session_key:
            raise ValidationError(
                _('Either author or session_key must be set.'),
                code='missing_author_session_key'
            )