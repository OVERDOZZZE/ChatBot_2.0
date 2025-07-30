from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from decouple import config
from django.http import HttpResponse, JsonResponse
import json
import requests
import re
from openai import OpenAI
from .models import InstaBotMessage, Product, ConversationSession, Purchase
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


def get_intent_prompt():
    return """Определи намерение клиента из его сообщения. Возможные намерения:
- ПОКУПКА: хочет купить товар, добавить в корзину, оформить заказ
- КАТАЛОГ: хочет посмотреть товары, узнать что есть в наличии
- ИНФОРМАЦИЯ: вопросы о товаре, цене, доставке
- ЖАЛОБА: недоволен товаром или сервисом
- ПРОЧЕЕ: общие вопросы, приветствие

Ответь только одним словом: ПОКУПКА, КАТАЛОГ, ИНФОРМАЦИЯ, ЖАЛОБА или ПРОЧЕЕ."""


def get_system_prompt_by_state(state, session=None):
    prompts = {
        'idle': """Ты — вежливый помощник магазина триммеров и товаров для парикмахеров в Бишкеке. 
Отвечай кратко и по делу. Доставка по Бишкеку бесплатная. 
Предложи посмотреть каталог или помоги с вопросами.""",

        'browsing': """Ты показываешь каталог товаров. Предоставь информацию о доступных товарах 
из базы данных. Помоги клиенту выбрать товар и добавить в корзину.""",

        'purchase_product_selection': """Клиент добавляет товары в корзину. Помоги выбрать товары, 
показывай цены и наличие. После выбора товаров предложи оформить заказ.""",

        'purchase_collecting_phone': """Собери номер телефона клиента для заказа. 
Объясни, что номер нужен для связи по доставке. Проверь, что номер введен корректно.""",

        'purchase_collecting_address': """Собери адрес доставки. Уточни точный адрес в Бишкеке 
для бесплатной доставки.""",

        'purchase_confirmation': """Покажи итоговую информацию о заказе: товары, количество, 
общую сумму, адрес доставки. Попроси подтвердить заказ словом 'Подтвердить'.""",

        'complaint': """Обрабатывай жалобу клиента вежливо и профессионально. 
Извинись и предложи решение проблемы.""",

        'inquiry': """Отвечай на общие вопросы о товарах, доставке, оплате. 
Будь информативным но кратким."""
    }

    base_prompt = prompts.get(state, prompts['idle'])

    if session and session.get_selected_products():
        cart_info = f"\nТекущая корзина клиента: {format_cart(session)}"
        base_prompt += cart_info

    return base_prompt


def format_cart(session):
    """Format cart contents for display"""
    products = session.get_selected_products()
    if not products:
        return "Корзина пуста"

    cart_text = []
    total = 0

    for item in products:
        try:
            product = Product.objects.get(id=item['product_id'])
            quantity = item['quantity']
            subtotal = product.price * quantity
            total += subtotal
            cart_text.append(f"• {product.name} x{quantity} = {subtotal} сом")
        except Product.DoesNotExist:
            continue

    cart_text.append(f"\nИтого: {total} сом")
    return "\n".join(cart_text)


def format_product_catalog():
    """Format available products for display"""
    products = Product.objects.filter(available=True)
    if not products:
        return "К сожалению, товаров нет в наличии."

    catalog_text = ["📋 Наши товары:\n"]

    for product in products:
        catalog_text.append(f"🔹 {product.name}")
        catalog_text.append(f"   Цена: {product.price} сом")
        catalog_text.append(f"   {product.description}\n")

    catalog_text.append("Доставка по Бишкеку бесплатная! 🚚")
    return "\n".join(catalog_text)


def extract_product_from_message(message):
    """Extract product selection from user message"""
    # Try to find product by name (case insensitive)
    products = Product.objects.filter(available=True)

    for product in products:
        if product.name.lower() in message.lower():
            # Try to extract quantity
            quantity_match = re.search(r'(\d+)\s*шт|(\d+)\s*штук|(\d+)\s*штуки', message.lower())
            quantity = 1
            if quantity_match:
                quantity = int(quantity_match.group(1) or quantity_match.group(2) or quantity_match.group(3))

            return product.id, quantity

    return None, None


def extract_phone_from_message(message):
    """Extract phone number from message"""
    # Look for phone patterns
    phone_patterns = [
        r'\+996\s*\d{3}\s*\d{3}\s*\d{3}',
        r'0\d{3}\s*\d{3}\s*\d{3}',
        r'\d{3}\s*\d{3}\s*\d{3}'
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, message)
        if match:
            return match.group().replace(' ', '')

    return None


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
            for entry in data.get("entry", []):
                if 'messaging' in entry:
                    process_message(entry['messaging'])
                elif 'comments' in entry:
                    process_comment(entry['comments'])
                elif 'mention' in entry:
                    process_mention(entry['mention'])

            return JsonResponse({"status": "Event processed"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


def privacy_policy(request):
    return render(request, 'privacy_policy.html')


def home_page(request):
    return render(request, 'home.html')


def process_message(data):
    for event in data:
        message = event.get("message", {})
        sender_id = event.get("sender", {}).get("id")

        if sender_id == BOT_ID:
            continue

        text = message.get("text")
        if not text:
            continue

        # Clean up old messages
        expiry = timezone.now() - timedelta(hours=24)
        InstaBotMessage.objects.filter(sender_id=sender_id, timestamp__lt=expiry).delete()

        # Save user message
        InstaBotMessage.objects.create(
            sender_id=sender_id,
            role="user",
            content=text
        )

        # Get or create session
        session, created = ConversationSession.objects.get_or_create(
            sender_id=sender_id,
            defaults={'current_state': 'idle'}
        )

        # Process message based on current state
        reply = handle_conversation_flow(session, text)

        # Save bot response
        InstaBotMessage.objects.create(
            sender_id=sender_id,
            role="assistant",
            content=reply
        )

        send_message(reply, str(sender_id))


def handle_conversation_flow(session, user_message):
    """Main conversation flow handler"""

    # Check for confirmation word first
    if user_message.strip().lower() == "подтвердить" and session.current_state == 'purchase_confirmation':
        return handle_purchase_confirmation(session, user_message)

    # Handle different states
    if session.current_state == 'idle':
        return handle_idle_state(session, user_message)

    elif session.current_state == 'browsing':
        return handle_browsing_state(session, user_message)

    elif session.current_state == 'purchase_product_selection':
        return handle_product_selection_state(session, user_message)

    elif session.current_state == 'purchase_collecting_phone':
        return handle_phone_collection_state(session, user_message)

    elif session.current_state == 'purchase_collecting_address':
        return handle_address_collection_state(session, user_message)

    elif session.current_state == 'purchase_confirmation':
        return handle_confirmation_state(session, user_message)

    elif session.current_state == 'complaint':
        return handle_complaint_state(session, user_message)

    elif session.current_state == 'inquiry':
        return handle_inquiry_state(session, user_message)

    else:
        session.reset_session()
        return "Что-то пошло не так. Начнем сначала. Чем могу помочь?"


def handle_idle_state(session, user_message):
    """Handle messages when bot is in idle state"""

    # Classify intent using AI
    intent = classify_intent(user_message)

    if intent == 'КАТАЛОГ':
        session.current_state = 'browsing'
        session.save()
        return f"📋 Вот наш каталог:\n\n{format_product_catalog()}\n\nЧто вас интересует?"

    elif intent == 'ПОКУПКА':
        session.current_state = 'purchase_product_selection'
        session.save()
        return f"Отлично! Давайте выберем товары:\n\n{format_product_catalog()}\n\nНапишите название товара, который хотите купить."

    elif intent == 'ИНФОРМАЦИЯ':
        session.current_state = 'inquiry'
        session.save()
        return generate_ai_response(session, user_message)

    elif intent == 'ЖАЛОБА':
        session.current_state = 'complaint'
        session.save()
        return "Мне очень жаль, что у вас возникли проблемы. Расскажите подробнее, что случилось, и я постараюсь помочь."

    else:
        return generate_ai_response(session, user_message)


def handle_browsing_state(session, user_message):
    """Handle browsing catalog state"""

    # Check if user wants to buy something
    if any(word in user_message.lower() for word in ['купить', 'заказать', 'хочу', 'возьму']):
        session.current_state = 'purchase_product_selection'
        session.save()
        return "Отлично! Напишите название товара, который хотите купить."

    return generate_ai_response(session, user_message)


def handle_product_selection_state(session, user_message):
    """Handle product selection for purchase"""

    # Check for product in message
    product_id, quantity = extract_product_from_message(user_message)

    if product_id:
        session.add_product(product_id, quantity)
        session.save()

        product = Product.objects.get(id=product_id)
        response = f"✅ Добавил в корзину: {product.name} x{quantity}\n\n"
        response += f"Ваша корзина:\n{format_cart(session)}\n\n"
        response += "Хотите добавить еще товары или оформить заказ?"
        return response

    # Check if wants to proceed to order
    if any(word in user_message.lower() for word in ['заказ', 'оформить', 'купить', 'хватит', 'достаточно']):
        if session.get_selected_products():
            session.current_state = 'purchase_collecting_phone'
            session.save()
            return f"Отлично! Ваши товары:\n{format_cart(session)}\n\nДля оформления заказа нужен ваш номер телефона:"
        else:
            return "Ваша корзина пуста. Сначала выберите товары из каталога."

    return f"Извините, не нашел такой товар. Вот что у нас есть:\n\n{format_product_catalog()}"


def handle_phone_collection_state(session, user_message):
    """Handle phone number collection"""

    phone = extract_phone_from_message(user_message)

    if phone:
        session.collected_phone = phone
        session.current_state = 'purchase_collecting_address'
        session.save()
        return "Спасибо! Теперь укажите адрес доставки в Бишкеке:"

    return "Пожалуйста, укажите корректный номер телефона (например: +996 555 123 456 или 0555 123 456):"


def handle_address_collection_state(session, user_message):
    """Handle address collection"""

    if len(user_message.strip()) > 10:  # Basic validation
        session.collected_address = user_message.strip()
        session.current_state = 'purchase_confirmation'
        session.save()

        # Prepare order summary
        products_info = []
        total = 0

        for item in session.get_selected_products():
            try:
                product = Product.objects.get(id=item['product_id'])
                quantity = item['quantity']
                subtotal = product.price * quantity
                total += subtotal
                products_info.append(f"• {product.name} x{quantity} = {subtotal} сом")
            except Product.DoesNotExist:
                continue

        summary = f"📋 Подтверждение заказа:\n\n"
        summary += "\n".join(products_info)
        summary += f"\n\nИтого: {total} сом"
        summary += f"\nТелефон: {session.collected_phone}"
        summary += f"\nАдрес: {session.collected_address}"
        summary += f"\nДоставка: БЕСПЛАТНО"
        summary += f"\n\n✅ Для подтверждения заказа напишите: Подтвердить"

        return summary

    return "Пожалуйста, укажите подробный адрес доставки:"


def handle_confirmation_state(session, user_message):
    """Handle order confirmation"""

    if user_message.strip().lower() != "подтвердить":
        return "Для подтверждения заказа напишите точно: Подтвердить"

    return handle_purchase_confirmation(session, user_message)


def handle_purchase_confirmation(session, user_message):
    """Process confirmed purchase"""

    try:
        # Prepare products data for Purchase model
        products_data = []
        total_amount = 0

        for item in session.get_selected_products():
            try:
                product = Product.objects.get(id=item['product_id'])
                quantity = item['quantity']
                subtotal = product.price * quantity
                total_amount += subtotal

                products_data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity': quantity,
                    'price': float(product.price),
                    'subtotal': float(subtotal)
                })
            except Product.DoesNotExist:
                continue

        # Create purchase record
        purchase = Purchase.objects.create(
            sender_id=session.sender_id,
            phone_number=session.collected_phone,
            address=session.collected_address,
            customer_last_message=user_message,
            total_amount=total_amount
        )
        purchase.set_products_data(products_data)
        purchase.save()

        # Reset session
        session.reset_session()

        response = f"🎉 Заказ №{purchase.id} подтвержден!\n\n"
        response += f"Мы свяжемся с вами по телефону {purchase.phone_number} для уточнения деталей доставки.\n\n"
        response += f"Доставка по адресу: {purchase.address}\n"
        response += f"Сумма заказа: {total_amount} сом\n"
        response += f"Доставка: БЕСПЛАТНО\n\n"
        response += "Спасибо за покупку! 😊"

        return response

    except Exception as e:
        return f"Произошла ошибка при оформлении заказа. Попробуйте еще раз или свяжитесь с нами напрямую."


def handle_complaint_state(session, user_message):
    """Handle customer complaints"""

    session.current_state = 'idle'
    session.save()

    response = generate_ai_response(session, user_message)
    response += "\n\nВаша жалоба принята. Мы обязательно разберем ситуацию."

    return response


def handle_inquiry_state(session, user_message):
    """Handle general inquiries"""

    session.current_state = 'idle'
    session.save()

    return generate_ai_response(session, user_message)


def classify_intent(user_message):
    """Classify user intent using AI"""

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=[
                {"role": "system", "content": get_intent_prompt()},
                {"role": "user", "content": user_message}
            ]
        )

        intent = completion.choices[0].message.content.strip().upper()

        if intent in ['ПОКУПКА', 'КАТАЛОГ', 'ИНФОРМАЦИЯ', 'ЖАЛОБА', 'ПРОЧЕЕ']:
            return intent
        else:
            return 'ПРОЧЕЕ'

    except:
        return 'ПРОЧЕЕ'


def generate_ai_response(session, user_message):
    """Generate AI response based on current state"""

    # Get recent messages for context
    recent_messages = InstaBotMessage.objects.filter(
        sender_id=session.sender_id
    ).order_by('-timestamp')[:MAX_HISTORY_LENGTH]
    recent_messages = list(reversed(recent_messages))

    # Prepare context
    messages = [{"role": "system", "content": get_system_prompt_by_state(session.current_state, session)}]

    # Add product catalog to context
    if session.current_state in ['browsing', 'purchase_product_selection']:
        products_context = f"Доступные товары:\n{format_product_catalog()}"
        messages.append({"role": "system", "content": products_context})

    # Add conversation history
    messages += [{"role": msg.role, "content": msg.content} for msg in recent_messages[-5:]]  # Last 5 messages

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=messages
        )

        return completion.choices[0].message.content

    except Exception as e:
        return "Извините, произошла техническая ошибка. Попробуйте еще раз."


def send_message(reply, recipient_id):
    """Send message via Instagram Graph API"""

    url = f'https://graph.instagram.com/v21.0/me/messages'
    headers = {
        'Authorization': f'Bearer {LONG_USER_ACCESS_TOKEN}',
        'Content-Type': "application/json"
    }
    json_body = {
        'recipient': {
            'id': int(recipient_id)
        },
        'message': {
            'text': str(reply)
        }
    }

    response = requests.post(url, headers=headers, json=json_body)
    return response.json()


def process_comment(data):
    """Handle Instagram comment events"""
    print("Comment Event Received:", data)


def process_mention(data):
    """Handle Instagram mention events"""
    print("Mention Event Received:", data)
