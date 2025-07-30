from django.db import models
from django.utils import timezone
import json


class InstaBotMessage(models.Model):
    sender_id = models.CharField(max_length=64)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.timestamp} - {self.sender_id} ({self.role}: {self.content[:50]}'


class Product(models.Model):
    CATEGORIES = (
        ('trimmers', 'Триммеры'),
        ('hair_clippers', 'Машинки для стрижки')
    )
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=255)
    category = models.CharField(choices=CATEGORIES, max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.price} сом"


class ConversationSession(models.Model):
    STATES = (
        ('idle', 'Ожидание'),
        ('browsing', 'Просмотр товаров'),
        ('purchase_product_selection', 'Выбор товаров'),
        ('purchase_collecting_phone', 'Сбор телефона'),
        ('purchase_collecting_address', 'Сбор адреса'),
        ('purchase_confirmation', 'Подтверждение заказа'),
        ('complaint', 'Обработка жалобы'),
        ('inquiry', 'Общий запрос'),
    )

    sender_id = models.CharField(max_length=64, unique=True)
    current_state = models.CharField(max_length=50, choices=STATES, default='idle')
    selected_products = models.TextField(blank=True, null=True)  # JSON field for multiple products
    collected_phone = models.CharField(max_length=20, blank=True, null=True)
    collected_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_selected_products(self):
        """Return list of selected products with quantities"""
        if self.selected_products:
            return json.loads(self.selected_products)
        return []

    def set_selected_products(self, products_list):
        """Set selected products as JSON"""
        self.selected_products = json.dumps(products_list)

    def add_product(self, product_id, quantity=1):
        """Add product to cart or increase quantity"""
        products = self.get_selected_products()

        # Check if product already in cart
        for item in products:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                break
        else:
            # Product not in cart, add new
            products.append({'product_id': product_id, 'quantity': quantity})

        self.set_selected_products(products)

    def remove_product(self, product_id):
        """Remove product from cart"""
        products = self.get_selected_products()
        products = [item for item in products if item['product_id'] != product_id]
        self.set_selected_products(products)

    def get_total_price(self):
        """Calculate total price of all selected products"""
        total = 0
        products = self.get_selected_products()

        for item in products:
            try:
                product = Product.objects.get(id=item['product_id'])
                total += product.price * item['quantity']
            except Product.DoesNotExist:
                continue

        return total

    def clear_cart(self):
        """Clear all selected products"""
        self.selected_products = None

    def reset_session(self):
        """Reset session to idle state"""
        self.current_state = 'idle'
        self.selected_products = None
        self.collected_phone = None
        self.collected_address = None
        self.save()

    def __str__(self):
        return f"{self.sender_id} - {self.current_state}"


class Purchase(models.Model):
    sender_id = models.CharField(max_length=64)
    products_data = models.TextField()  # JSON field with products and quantities
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    customer_last_message = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def get_products_data(self):
        """Return products data as list"""
        return json.loads(self.products_data)

    def set_products_data(self, products_list):
        """Set products data as JSON"""
        self.products_data = json.dumps(products_list, ensure_ascii=False)

    def __str__(self):
        return f"Заказ {self.id} - {self.sender_id} - {self.total_amount} сом"


# Keep your existing Customer model for backward compatibility
class Customer(models.Model):
    sender_id = models.CharField(max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=255)
    address = models.TextField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_id} - {self.product.name}"

