from django.urls import path
from .views import *

urlpatterns = [
    path('get_authorization_code_url/', get_authorization_code_url, name='get_authorization_code_url'),
    path('get_authorization_code/', get_authorization_code, name='get_authorization_code'),
    path('get_user_access_token/', get_user_access_token, name='get_user_access_token'),
    path('get_long_user_access_token/', get_long_user_access_token, name='get_long_user_access_token'),
]
