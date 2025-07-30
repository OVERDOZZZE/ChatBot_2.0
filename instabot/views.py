from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from decouple import config
from django.http import HttpResponse, JsonResponse
import json
import requests
from openai import OpenAI
from .models import InstaBotMessage
from django.utils import timezone
from datetime import timedelta


VERIFY_TOKEN = config('VERIFY_TOKEN')
LONG_USER_ACCESS_TOKEN = config('LONG_USER_ACCESS_TOKEN')
OPENAI_API_KEY = config('OPENAI_API_KEY')
BOT_ID = config('BOT_ID')
MAX_HISTORY_LENGTH = 10

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENAI_API_KEY,
)

SYSTEM_PROMPT = (
    "Ты — assistant, вежливый и лаконичный помощник магазина в Бишкеке, который продаёт триммеры "
    "и товары для парикмахеров. Отвечай строго по сути заданного вопроса: без лишних "
    "деталей, рекламы или навязчивости. Уточни наличие, цену, способ оплаты, условия "
    "доставки — только если об этом спрашивают. Доставка по Бишкеку бесплатная. "
    "Цель — дать уверенный и спокойный ответ, не отпугнуть клиента."
)


@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse('Invalid Verification Token', status=403)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            print('------- Event received')
            for entry in data.get("entry", []):
                if 'messaging' in entry:
                    process_message(entry['messaging'])
                elif 'comments' in entry:
                    process_comment(entry['comments'])
                elif 'mention' in entry:
                    process_mention(entry['mention'])
                else:
                    print("⚠️ Unhandled entry:", entry)

            return JsonResponse({"status": "Event processed"})

        except Exception as e:
            print("Error processing webhook:", e)
            return JsonResponse({"error": str(e)}, status=400)


def privacy_policy(request):
    return render(request, 'privacy_policy.html')


def home_page(request):
    return render(request, 'home.html')


def process_message(data):
    print("Message Event Received:")
    print('Processing event... it may take a moment')

    for event in data:
        message = event.get("message", {})
        sender_id = event.get("sender", {}).get("id")

        if sender_id == BOT_ID:
            print("Ignoring message from bot itself.")
            continue

        text = message.get("text")
        if not text:
            continue

        # 🧹 Optional cleanup: remove messages older than 24 hours
        expiry = timezone.now() - timedelta(hours=24)
        InstaBotMessage.objects.filter(sender_id=sender_id, timestamp__lt=expiry).delete()

        # 💬 Save user's new message
        InstaBotMessage.objects.create(
            sender_id=sender_id,
            role="user",
            content=text
        )

        # 📜 Fetch recent history (after cleanup)
        recent_messages = InstaBotMessage.objects.filter(
            sender_id=sender_id
        ).order_by('-timestamp')[:MAX_HISTORY_LENGTH]

        # Reverse for chronological order
        recent_messages = list(reversed(recent_messages))

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": msg.role, "content": msg.content} for msg in recent_messages]
        print(messages)
        # 🧠 Call AI
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=messages
        )
        reply = completion.choices[0].message.content
        print('REPLY: ', reply)

        # 💬 Save bot's reply
        InstaBotMessage.objects.create(
            sender_id=sender_id,
            role="assistant",
            content=reply
        )

        send_message(reply, str(sender_id))


def send_message(reply, recipient_id):
    url = f'https://graph.instagram.com/v21.0/me/messages'
    headers = {'Authorization': f'Bearer {LONG_USER_ACCESS_TOKEN}', 'Content-Type': "application/json"}
    json_body = {
        'recipient': {
            'id': int(recipient_id)
        },
        'message': {
            'text': str(reply)
        }
    }
    response = requests.post(url, headers=headers, json=json_body)
    data = response.json()
    print(data)


def process_comment(data):
    print("Comment Event Received:")


def process_mention(data):
    print("Mention Event Received:")

