"""
Custom exception handler for DRF to wrap all error responses.
Place this in: apps/core/exception_handler.py
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from .response_utils import format_serializer_errors


def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps all exceptions in standard envelope.
    """
    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)
    
    # If DRF handled it, wrap the response
    if response is not None:
        error_data = {
            "status": "error",
            "message": get_error_message(exc, response),
        }
        
        # Add detailed errors if available
        if hasattr(response, 'data') and response.data:
            if isinstance(response.data, dict):
                # Format serializer errors nicely
                if 'detail' in response.data:
                    # Single error message
                    error_data['message'] = str(response.data['detail'])
                else:
                    # Field validation errors
                    error_data['errors'] = format_serializer_errors(response.data)
            elif isinstance(response.data, list):
                error_data['errors'] = response.data
        
        response.data = error_data
        return response
    
    # Handle Django's Http404
    if isinstance(exc, Http404):
        return Response({
            "status": "error",
            "message": "Resource not found",
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Handle Django's ValidationError
    if isinstance(exc, DjangoValidationError):
        return Response({
            "status": "error",
            "message": "Validation error",
            "errors": exc.message_dict if hasattr(exc, 'message_dict') else list(exc.messages),
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # For unhandled exceptions, return a generic error
    return Response({
        "status": "error",
        "message": "An unexpected error occurred",
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_error_message(exc, response):
    """Extract appropriate error message from exception."""
    if hasattr(exc, 'default_detail'):
        return str(exc.default_detail)
    elif hasattr(exc, 'detail'):
        detail = exc.detail
        if isinstance(detail, dict):
            # Return first error message
            for key, value in detail.items():
                if isinstance(value, list) and value:
                    return str(value[0])
                return str(value)
        return str(detail)
    return "An error occurred"