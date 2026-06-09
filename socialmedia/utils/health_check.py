"""
Health check views for monitoring and deployment verification
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.core.cache import cache
import redis
import os


@require_http_methods(["GET"])
def health_check(request):
    """
    Main health check endpoint
    Returns comprehensive system status
    """
    
    health_status = {
        "status": "healthy",
        "service": "aetheria",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "ok",
            "message": "Database connected"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = {
            "status": "error",
            "message": str(e)
        }
    
    # Check Cache
    try:
        cache.set("health_check", "ok", 60)
        if cache.get("health_check") == "ok":
            health_status["checks"]["cache"] = {
                "status": "ok",
                "message": "Cache system working"
            }
        else:
            health_status["checks"]["cache"] = {
                "status": "warning",
                "message": "Cache read/write failed"
            }
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "warning",
            "message": f"Cache error: {str(e)}"
        }
    
    # Check Redis (if configured)
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            r.ping()
            health_status["checks"]["redis"] = {
                "status": "ok",
                "message": "Redis connected"
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "warning",
                "message": f"Redis error: {str(e)}"
            }
    else:
        health_status["checks"]["redis"] = {
            "status": "not_configured",
            "message": "Redis not configured"
        }
    
    # Check Debug Mode
    debug_mode = os.environ.get("DEBUG", "True") == "True"
    health_status["checks"]["debug_mode"] = {
        "status": "warning" if debug_mode else "ok",
        "value": debug_mode,
        "message": "Debug mode ON (production issue!)" if debug_mode else "Debug mode OFF"
    }
    
    # Overall status
    if any(check.get("status") == "error" for check in health_status["checks"].values()):
        health_status["status"] = "unhealthy"
    elif any(check.get("status") == "warning" for check in health_status["checks"].values()):
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] != "unhealthy" else 503
    
    return JsonResponse(health_status, status=status_code)


@require_http_methods(["GET"])
def ready_check(request):
    """
    Ready check endpoint for deployment verification
    Used by orchestration systems to check if app is ready to serve traffic
    """
    
    checks = {
        "ready": True,
        "services": {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["services"]["database"] = True
    except:
        checks["ready"] = False
        checks["services"]["database"] = False
    
    # Check cache
    try:
        cache.set("ready_check", "ok", 10)
        checks["services"]["cache"] = cache.get("ready_check") == "ok"
    except:
        checks["services"]["cache"] = False
    
    status_code = 200 if checks["ready"] else 503
    return JsonResponse(checks, status=status_code)


@require_http_methods(["GET"])
def alive_check(request):
    """
    Simple liveness check endpoint
    Just verifies the application process is running
    """
    return JsonResponse({
        "alive": True,
        "service": "aetheria"
    }, status=200)
