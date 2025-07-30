from django.core.management.base import BaseCommand
from django.utils import timezone
from decouple import config
from openai import OpenAI
import time


class Command(BaseCommand):
    help = 'Check AI API health and performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-count',
            type=int,
            default=5,
            help='Number of test requests to send (default: 5)',
        )

    def handle(self, *args, **options):
        OPENAI_API_KEY = config('OPENAI_API_KEY')
        test_count = options['test_count']

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENAI_API_KEY,
        )

        self.stdout.write(self.style.SUCCESS('=== ПРОВЕРКА AI API ==='))
        self.stdout.write(f'Отправляю {test_count} тестовых запросов...\n')

        successful_requests = 0
        total_response_time = 0
        failed_requests = []

        for i in range(test_count):
            self.stdout.write(f'Запрос {i + 1}/{test_count}... ', ending='')

            start_time = time.time()
            try:
                completion = client.chat.completions.create(
                    model="z-ai/glm-4.5-air:free",
                    messages=[
                        {"role": "system", "content": "Ответь кратко на русском языке"},
                        {"role": "user", "content": f"Тест {i + 1}"}
                    ],
                    timeout=10,
                    max_tokens=50
                )

                end_time = time.time()
                response_time = end_time - start_time

                if completion.choices[0].message.content:
                    successful_requests += 1
                    total_response_time += response_time
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Успешно ({response_time:.2f}с)')
                    )
                else:
                    failed_requests.append(f"Запрос {i + 1}: Пустой ответ")
                    self.stdout.write(self.style.ERROR('✗ Пустой ответ'))

            except Exception as e:
                failed_requests.append(f"Запрос {i + 1}: {str(e)}")
                self.stdout.write(self.style.ERROR(f'✗ Ошибка: {str(e)[:50]}...'))

        # Results summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('РЕЗУЛЬТАТЫ:'))
        self.stdout.write(f'Успешных запросов: {successful_requests}/{test_count}')
        self.stdout.write(f'Процент успеха: {(successful_requests / test_count) * 100:.1f}%')

        if successful_requests > 0:
            avg_response_time = total_response_time / successful_requests
            self.stdout.write(f'Среднее время ответа: {avg_response_time:.2f} секунд')

        if failed_requests:
            self.stdout.write('\nОШИБКИ:')
            for error in failed_requests:
                self.stdout.write(self.style.ERROR(f'• {error}'))

        # Health status
        success_rate = (successful_requests / test_count) * 100
        if success_rate >= 80:
            self.stdout.write(self.style.SUCCESS('\n🟢 API РАБОТАЕТ НОРМАЛЬНО'))
        elif success_rate >= 50:
            self.stdout.write(self.style.WARNING('\n🟡 API РАБОТАЕТ С ПРОБЛЕМАМИ'))
        else:
            self.stdout.write(self.style.ERROR('\n🔴 API НЕ РАБОТАЕТ'))

        # Recommendations
        if success_rate < 80:
            self.stdout.write('\nРЕКОМЕНДАЦИИ:')
            self.stdout.write('• Проверьте интернет соединение')
            self.stdout.write('• Убедитесь, что API ключ валиден')
            self.stdout.write('• Проверьте лимиты OpenRouter')
            self.stdout.write('• Рассмотрите использование другой модели')