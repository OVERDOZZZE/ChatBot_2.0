from django.contrib import admin
from .models import InstaBotMessage, Product, ConversationSession, Purchase, Customer
import json


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'available', 'created_display']
    list_filter = ['category', 'available']
    search_fields = ['name', 'description']
    list_editable = ['available', 'price']

    def created_display(self, obj):
        return "Товар"

    created_display.short_description = 'Статус'


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender_id', 'phone_number', 'total_amount', 'timestamp', 'products_summary']
    list_filter = ['timestamp']
    search_fields = ['sender_id', 'phone_number', 'address']
    readonly_fields = ['timestamp', 'products_detail', 'customer_last_message']

    def products_summary(self, obj):
        try:
            products_data = obj.get_products_data()
            summary = []
            for item in products_data:
                summary.append(f"{item['product_name']} x{item['quantity']}")
            return ", ".join(summary)
        except:
            return "Ошибка загрузки"

    products_summary.short_description = 'Товары'

    def products_detail(self, obj):
        try:
            products_data = obj.get_products_data()
            detail = []
            for item in products_data:
                detail.append(
                    f"• {item['product_name']} x{item['quantity']} = {item['subtotal']} сом"
                )
            return "\n".join(detail)
        except:
            return "Ошибка загрузки данных"

    products_detail.short_description = 'Детали заказа'


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ['sender_id', 'current_state', 'cart_summary', 'updated_at']
    list_filter = ['current_state', 'updated_at']
    search_fields = ['sender_id']
    readonly_fields = ['created_at', 'updated_at', 'cart_detail']
    actions = ['reset_sessions']

    def cart_summary(self, obj):
        products = obj.get_selected_products()
        if not products:
            return "Пусто"
        return f"{len(products)} товар(ов)"

    cart_summary.short_description = 'Корзина'

    def cart_detail(self, obj):
        products = obj.get_selected_products()
        if not products:
            return "Корзина пуста"

        try:
            from .models import Product
            detail = []
            total = 0
            for item in products:
                try:
                    product = Product.objects.get(id=item['product_id'])
                    quantity = item['quantity']
                    subtotal = product.price * quantity
                    total += subtotal
                    detail.append(f"• {product.name} x{quantity} = {subtotal} сом")
                except Product.DoesNotExist:
                    detail.append(f"• Товар ID:{item['product_id']} (не найден) x{item['quantity']}")

            detail.append(f"\nИтого: {total} сом")
            return "\n".join(detail)
        except:
            return "Ошибка загрузки корзины"

    cart_detail.short_description = 'Содержимое корзины'

    def reset_sessions(self, request, queryset):
        count = 0
        for session in queryset:
            session.reset_session()
            count += 1
        self.message_user(request, f'Сброшено {count} сессий.')

    reset_sessions.short_description = 'Сбросить выбранные сессии'


@admin.register(InstaBotMessage)
class InstaBotMessageAdmin(admin.ModelAdmin):
    list_display = ['sender_id', 'role', 'content_preview', 'timestamp']
    list_filter = ['role', 'timestamp']
    search_fields = ['sender_id', 'content']
    readonly_fields = ['timestamp']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content

    content_preview.short_description = 'Сообщение'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['sender_id', 'product', 'phone_number', 'timestamp']
    list_filter = ['timestamp', 'product']
    search_fields = ['sender_id', 'phone_number']
    readonly_fields = ['timestamp']

