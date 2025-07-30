from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from instabot.models import InstaBotMessage, ConversationSession, Purchase, Product


class Command(BaseCommand):
    help = 'Show bot statistics'

    def handle(self, *args, **options):
        # Active sessions
        active_sessions = ConversationSession.objects.exclude(current_state='idle').count()
        total_sessions = ConversationSession.objects.count()

        # Messages today
        today = timezone.now().date()
        messages_today = InstaBotMessage.objects.filter(timestamp__date=today).count()

        # Purchases
        total_purchases = Purchase.objects.count()
        purchases_today = Purchase.objects.filter(timestamp__date=today).count()

        # Revenue
        total_revenue = sum(p.total_amount for p in Purchase.objects.all())
        revenue_today = sum(p.total_amount for p in Purchase.objects.filter(timestamp__date=today))

        # Products
        total_products = Product.objects.count()
        available_products = Product.objects.filter(available=True).count()

        self.stdout.write(self.style.SUCCESS('=== СТАТИСТИКА БОТА ==='))
        self.stdout.write(f'Активных сессий: {active_sessions} из {total_sessions}')
        self.stdout.write(f'Сообщений сегодня: {messages_today}')
        self.stdout.write(f'Заказов всего: {total_purchases}')
        self.stdout.write(f'Заказов сегодня: {purchases_today}')
        self.stdout.write(f'Общая выручка: {total_revenue} сом')
        self.stdout.write(f'Выручка сегодня: {revenue_today} сом')
        self.stdout.write(f'Товаров: {available_products} из {total_products} доступно')

