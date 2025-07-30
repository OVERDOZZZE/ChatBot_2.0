from django.db import models


class InstaBotMessage(models.Model):
    sender_id = models.CharField(max_length=64)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.timestamp} - {self.sender_id} ({self.role}: {self.content[:50]}'
