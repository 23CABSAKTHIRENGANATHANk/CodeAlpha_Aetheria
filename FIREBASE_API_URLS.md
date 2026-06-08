# Device Token Registration API Endpoint
# Add this to socialmedia/users/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... existing patterns ...
    
    # Firebase Device Token Registration
    path('api/register-device-token/', views.register_device_token, name='register_device_token'),
    path('api/unregister-device-token/', views.unregister_device_token, name='unregister_device_token'),
    path('api/device-tokens/', views.list_device_tokens, name='list_device_tokens'),
]
