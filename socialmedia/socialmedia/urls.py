"""
URL configuration for socialmedia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import os

# Import health check views
from utils.health_check import health_check, ready_check, alive_check

def service_worker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    try:
        with open(sw_path, 'rb') as f:
            return HttpResponse(f.read(), content_type="application/javascript")
    except FileNotFoundError:
        return HttpResponse(status=404)

def manifest_json(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    try:
        with open(manifest_path, 'rb') as f:
            return HttpResponse(f.read(), content_type="application/json")
    except FileNotFoundError:
        return HttpResponse(status=404)

urlpatterns = [
    # Health checks (monitoring/deployment)
    path("health/", health_check, name="health_check"),
    path("health", health_check, name="health_check_no_slash"),
    path("ready/", ready_check, name="ready_check"),
    path("ready", ready_check, name="ready_check_no_slash"),
    path("alive/", alive_check, name="alive_check"),
    path("alive", alive_check, name="alive_check_no_slash"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Service worker and manifest
    path("sw.js", service_worker, name="sw_js"),
    path("manifest.json", manifest_json, name="manifest_json"),
    
    # App URLs
    path("", include("users.urls")),
    path("", include("posts.urls")),
]

from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# ──────────────────────────────────────────────
# ERROR HANDLERS (SECURITY)
# ──────────────────────────────────────────────

from users.views import csrf_failure_view, permission_denied_view, page_not_found_view, server_error_view

handler403 = permission_denied_view
handler404 = page_not_found_view
handler500 = server_error_view

