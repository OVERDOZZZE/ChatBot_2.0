from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from instabot.models import InstaBotMessage, ConversationSession


class Command(BaseCommand):
    help = 'Clean up old bot data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to keep data (default: 7)',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        # Clean old messages
        old_messages = InstaBotMessage.objects.filter(timestamp__lt=cutoff_date)
        message_count = old_messages.count()
        old_messages.delete()

        # Clean old sessions
        old_sessions = ConversationSession.objects.filter(updated_at__lt=cutoff_date)
        session_count = old_sessions.count()
        old_sessions.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Удалено {message_count} старых сообщений и {session_count} старых сессий.'
            )
        )

