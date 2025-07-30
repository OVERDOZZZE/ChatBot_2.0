from django.contrib import admin
from .models import InstaBotMessage


@admin.register(InstaBotMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "sender_id", "role", "short_content")
    list_filter = ("role", "sender_id")
    ordering = ("-timestamp",)

    def short_content(self, obj):
        return obj.content[:80]

