"""
This migration adds a 'session_id' field to the 'chat' model.

The 'session_id' is a UUID field used for uniquely identifying chat sessions.
"""
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration class for adding a 'session_id' field to the 'chat' model."""
    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='session_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
