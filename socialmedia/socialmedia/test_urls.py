from django.http import HttpResponse
from django.urls import path, include

def ping(request):
    return HttpResponse('pong')

urlpatterns = [
    path('health/', ping),
    path('', include('users.urls')),
    path('', include('posts.urls')),
]
