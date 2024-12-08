# Generated by Django 5.1.3 on 2024-11-28 07:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sage_ref', '0003_alter_agent_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='agent',
            field=models.ForeignKey(blank=True, db_comment='References the agent who come to this room.', help_text='The agent who come to this room.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agent_room', to='sage_ref.agent', verbose_name='Agent'),
        ),
    ]