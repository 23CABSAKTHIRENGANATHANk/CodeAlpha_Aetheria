"""
Aetheria Error Handling Utilities
Provides consistent error handling and user-friendly error messages
"""

import logging
from typing import Dict, Any, Optional
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class AetheriaException(Exception):
    """Base exception for Aetheria application"""
    
    def __init__(self, message: str, error_code: str = "ERROR", status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AetheriaException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", 400)


class AuthenticationError(AetheriaException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR", 401)


class PermissionError(AetheriaException):
    """Raised when user lacks required permissions"""
    
    def __init__(self, message: str = "You don't have permission to perform this action"):
        super().__init__(message, "PERMISSION_ERROR", 403)


class NotFoundError(AetheriaException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource_type: str = "Resource"):
        message = f"{resource_type} not found"
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(AetheriaException):
    """Raised when there's a conflict (e.g., duplicate entry)"""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)


class RateLimitError(AetheriaException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message, "RATE_LIMIT", 429)


class ServerError(AetheriaException):
    """Raised for unexpected server errors"""
    
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(message, "SERVER_ERROR", 500)


def format_error_response(
    error: Exception,
    request_id: str = None,
    additional_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format exception into consistent error response
    
    Args:
        error: Exception instance
        request_id: Optional request tracking ID
        additional_data: Optional additional error context
        
    Returns:
        Formatted error response dictionary
    """
    
    if isinstance(error, AetheriaException):
        error_dict = {
            "success": False,
            "error": {
                "code": error.error_code,
                "message": error.message,
                "status_code": error.status_code,
            }
        }
        
        if hasattr(error, 'field') and error.field:
            error_dict["error"]["field"] = error.field
            
    else:
        # Generic server error
        error_dict = {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred",
                "status_code": 500,
            }
        }
        
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
    
    if request_id:
        error_dict["request_id"] = request_id
        
    if additional_data:
        error_dict["error"].update(additional_data)
        
    return error_dict


def error_response(
    error: Exception,
    request_id: str = None,
    additional_data: Dict[str, Any] = None
) -> Response:
    """
    Return formatted error response for API views
    
    Args:
        error: Exception instance
        request_id: Optional request tracking ID
        additional_data: Optional additional error context
        
    Returns:
        DRF Response with appropriate status code
    """
    
    error_dict = format_error_response(error, request_id, additional_data)
    status_code = error_dict["error"]["status_code"]
    
    return Response(error_dict, status=status_code)


# ============================================================
# COMMON ERROR MESSAGES
# ============================================================

ERROR_MESSAGES = {
    # Authentication
    "AUTH_REQUIRED": "Authentication required. Please login.",
    "INVALID_CREDENTIALS": "Invalid username or password.",
    "ACCOUNT_INACTIVE": "This account is inactive.",
    "EMAIL_NOT_VERIFIED": "Please verify your email address.",
    
    # Validation
    "USERNAME_TAKEN": "This username is already taken.",
    "EMAIL_TAKEN": "This email is already registered.",
    "PASSWORD_TOO_WEAK": "Password must be at least 8 characters with uppercase, lowercase, and number.",
    "INVALID_EMAIL": "Please enter a valid email address.",
    "INVALID_USERNAME": "Username can only contain letters, numbers, and underscores.",
    
    # Permissions
    "PERMISSION_DENIED": "You don't have permission to perform this action.",
    "OWNER_ONLY": "Only the owner can perform this action.",
    "ADMIN_ONLY": "Admin access required.",
    
    # Resources
    "USER_NOT_FOUND": "User not found.",
    "POST_NOT_FOUND": "Post not found.",
    "MESSAGE_NOT_FOUND": "Message not found.",
    "COMMENT_NOT_FOUND": "Comment not found.",
    
    # Business Logic
    "ALREADY_FOLLOWING": "You are already following this user.",
    "NOT_FOLLOWING": "You are not following this user.",
    "SELF_FOLLOW": "You cannot follow yourself.",
    "BLOCKED_USER": "This user has blocked you.",
    "CANNOT_UNBLOCK_SELF": "You cannot unblock yourself.",
    
    # File Upload
    "FILE_TOO_LARGE": "File is too large. Maximum size is 5MB.",
    "INVALID_FILE_TYPE": "Invalid file type. Allowed types: jpg, png, gif.",
    "FILE_UPLOAD_ERROR": "Error uploading file. Please try again.",
    
    # Rate Limiting
    "RATE_LIMIT_EXCEEDED": "Too many requests. Please try again in a few minutes.",
    
    # Server
    "SERVER_ERROR": "An unexpected error occurred. Please try again later.",
    "SERVICE_UNAVAILABLE": "Service temporarily unavailable. Please try again later.",
}


class ErrorHandler:
    """Utility class for handling errors consistently across the app"""
    
    @staticmethod
    def handle_validation_error(message: str, field: str = None) -> ValidationError:
        """Create validation error"""
        return ValidationError(message, field)
    
    @staticmethod
    def handle_auth_error(message: str = "Authentication failed") -> AuthenticationError:
        """Create authentication error"""
        return AuthenticationError(message)
    
    @staticmethod
    def handle_permission_error(message: str = None) -> PermissionError:
        """Create permission error"""
        msg = message or ERROR_MESSAGES.get("PERMISSION_DENIED")
        return PermissionError(msg)
    
    @staticmethod
    def handle_not_found(resource_type: str = "Resource") -> NotFoundError:
        """Create not found error"""
        return NotFoundError(resource_type)
    
    @staticmethod
    def handle_conflict_error(message: str) -> ConflictError:
        """Create conflict error"""
        return ConflictError(message)
    
    @staticmethod
    def handle_rate_limit() -> RateLimitError:
        """Create rate limit error"""
        return RateLimitError(ERROR_MESSAGES.get("RATE_LIMIT_EXCEEDED"))
    
    @staticmethod
    def handle_server_error(message: str = None) -> ServerError:
        """Create server error"""
        msg = message or ERROR_MESSAGES.get("SERVER_ERROR")
        return ServerError(msg)


# ============================================================
# DECORATORS
# ============================================================

def handle_errors(view_func):
    """Decorator to handle errors in API views"""
    
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except AetheriaException as e:
            logger.warning(f"Aetheria error: {e.message}")
            return error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return error_response(ServerError())
    
    return wrapper


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_username(username: str) -> None:
    """Validate username format"""
    import re
    
    if not username or len(username) < 3:
        raise ValidationError("Username must be at least 3 characters long.")
    
    if len(username) > 30:
        raise ValidationError("Username must be 30 characters or less.")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValidationError(
            ERROR_MESSAGES.get("INVALID_USERNAME"),
            field="username"
        )


def validate_email(email: str) -> None:
    """Validate email format"""
    from django.core.validators import validate_email as django_validate_email
    from django.core.exceptions import ValidationError as DjangoValidationError
    
    try:
        django_validate_email(email)
    except DjangoValidationError:
        raise ValidationError(
            ERROR_MESSAGES.get("INVALID_EMAIL"),
            field="email"
        )


def validate_password(password: str) -> None:
    """Validate password strength"""
    import re
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    
    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one number.")


print("✅ Error handling utilities loaded successfully")
