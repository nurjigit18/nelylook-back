"""
Custom renderer to wrap all successful responses in standard envelope.
Place this in: apps/core/renderers.py
"""
from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    """
    Renderer that wraps all responses in a standard envelope format.
    Only wraps if the response isn't already wrapped.
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        
        # Don't wrap if response is None or data is None
        if response is None or data is None:
            return super().render(data, accepted_media_type, renderer_context)
        
        # Don't wrap if already wrapped (has 'status' field)
        if isinstance(data, dict) and 'status' in data:
            return super().render(data, accepted_media_type, renderer_context)
        
        # Don't wrap schema/docs endpoints
        view = renderer_context.get('view')
        if view and hasattr(view, 'get_view_name'):
            view_name = view.get_view_name().lower()
            if any(x in view_name for x in ['schema', 'swagger', 'redoc', 'openapi']):
                return super().render(data, accepted_media_type, renderer_context)
        
        # Wrap successful responses
        status_code = response.status_code
        
        if 200 <= status_code < 300:
            # Check if it's a paginated response from DRF
            if isinstance(data, dict) and all(k in data for k in ['results', 'count']):
                # Paginated response
                wrapped_data = {
                    "status": "success",
                    "message": get_success_message(status_code),
                    "data": data['results'],
                    "pagination": {
                        "total_items": data['count'],
                        "next": data.get('next'),
                        "previous": data.get('previous'),
                    }
                }
            else:
                # Regular response
                wrapped_data = {
                    "status": "success",
                    "message": get_success_message(status_code),
                    "data": data,
                }
            
            return super().render(wrapped_data, accepted_media_type, renderer_context)
        
        # For error responses, they should already be wrapped by exception handler
        return super().render(data, accepted_media_type, renderer_context)


def get_success_message(status_code):
    """Get appropriate success message based on status code."""
    messages = {
        200: "Success",
        201: "Resource created successfully",
        202: "Request accepted",
        204: "Operation completed successfully",
    }
    return messages.get(status_code, "Success")