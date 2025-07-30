from django.urls import path
from .views import *

urlpatterns = [
    path('webhook/', webhook, name='webhook'),
    path('privacy_policy/', privacy_policy, name='privacy_policy'),
    path('', home_page, name='home_page')
]
