"""
Utility functions and classes for standardized API responses.
Place this in: apps/core/response_utils.py
"""
from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    Standardized API response wrapper that creates consistent JSON envelopes
    with status, message, and data fields.
    """
    
    @staticmethod
    def success(data=None, message="Success", status_code=status.HTTP_200_OK, **kwargs):
        """
        Create a successful response envelope.
        
        Args:
            data: The response data (dict, list, or None)
            message: Success message
            status_code: HTTP status code
            **kwargs: Additional fields to include in the envelope
        """
        envelope = {
            "status": "success",
            "message": message,
            "data": data,
        }
        envelope.update(kwargs)
        return Response(envelope, status=status_code)
    
    @staticmethod
    def error(message="An error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        """
        Create an error response envelope.
        
        Args:
            message: Error message
            errors: Detailed error information (dict or list)
            status_code: HTTP status code
            **kwargs: Additional fields to include in the envelope
        """
        envelope = {
            "status": "error",
            "message": message,
        }
        if errors:
            envelope["errors"] = errors
        envelope.update(kwargs)
        return Response(envelope, status=status_code)
    
    @staticmethod
    def created(data=None, message="Resource created successfully", **kwargs):
        """Shortcut for 201 Created responses."""
        return APIResponse.success(data, message, status.HTTP_201_CREATED, **kwargs)
    
    @staticmethod
    def no_content(message="Operation completed successfully"):
        """Shortcut for 204 No Content responses."""
        return APIResponse.success(None, message, status.HTTP_204_NO_CONTENT)
    
    @staticmethod
    def not_found(message="Resource not found", **kwargs):
        """Shortcut for 404 Not Found responses."""
        return APIResponse.error(message, status_code=status.HTTP_404_NOT_FOUND, **kwargs)
    
    @staticmethod
    def unauthorized(message="Authentication required", **kwargs):
        """Shortcut for 401 Unauthorized responses."""
        return APIResponse.error(message, status_code=status.HTTP_401_UNAUTHORIZED, **kwargs)
    
    @staticmethod
    def forbidden(message="Permission denied", **kwargs):
        """Shortcut for 403 Forbidden responses."""
        return APIResponse.error(message, status_code=status.HTTP_403_FORBIDDEN, **kwargs)
    
    @staticmethod
    def validation_error(errors, message="Validation failed", **kwargs):
        """Shortcut for validation error responses."""
        return APIResponse.error(message, errors=errors, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)
    
    @staticmethod
    def paginated(data, page, total_pages, total_items, message="Success", **kwargs):
        """
        Create a paginated response envelope.
        
        Args:
            data: List of items for current page
            page: Current page number
            total_pages: Total number of pages
            total_items: Total number of items
            message: Success message
            **kwargs: Additional pagination metadata
        """
        return APIResponse.success(
            data=data,
            message=message,
            pagination={
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items,
                **kwargs
            }
        )


def format_serializer_errors(serializer_errors):
    """
    Format DRF serializer errors into a more user-friendly structure.
    
    Args:
        serializer_errors: The serializer.errors dict
        
    Returns:
        Formatted error dict or list
    """
    formatted = {}
    for field, errors in serializer_errors.items():
        if isinstance(errors, list):
            formatted[field] = errors[0] if len(errors) == 1 else errors
        else:
            formatted[field] = str(errors)
    return formatted