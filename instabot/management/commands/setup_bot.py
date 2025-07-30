from django.core.management.base import BaseCommand
from django.utils import timezone
from instabot.models import Product


class Command(BaseCommand):
    help = 'Setup initial products for the bot'

    def handle(self, *args, **options):
        # Create sample products
        products_data = [
            {
                'name': 'Профессиональный триммер Wahl',
                'description': 'Высококачественный триммер для точной стрижки',
                'category': 'trimmers',
                'price': 3500,
                'available': True
            },
            {
                'name': 'Машинка для стрижки Moser',
                'description': 'Профессиональная машинка с керамическими ножами',
                'category': 'hair_clippers',
                'price': 4200,
                'available': True
            },
            {
                'name': 'Триммер для бороды Philips',
                'description': 'Компактный триммер для ухода за бородой',
                'category': 'trimmers',
                'price': 2800,
                'available': True
            },
            {
                'name': 'Машинка Remington HC5038',
                'description': 'Универсальная машинка для домашнего использования',
                'category': 'hair_clippers',
                'price': 1900,
                'available': True
            }
        ]

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Создан товар: {product.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Товар уже существует: {product.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Готово! Создано {created_count} новых товаров.')
        )

