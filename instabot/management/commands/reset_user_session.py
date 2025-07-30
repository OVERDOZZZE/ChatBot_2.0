from django.core.management.base import BaseCommand
from instabot.models import ConversationSession


class Command(BaseCommand):
    help = 'Reset specific user session'

    def add_arguments(self, parser):
        parser.add_argument('sender_id', type=str, help='Instagram sender ID')

    def handle(self, *args, **options):
        sender_id = options['sender_id']

        try:
            session = ConversationSession.objects.get(sender_id=sender_id)
            session.reset_session()
            self.stdout.write(
                self.style.SUCCESS(f'Сессия пользователя {sender_id} сброшена.')
            )
        except ConversationSession.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Сессия пользователя {sender_id} не найдена.')
            )
