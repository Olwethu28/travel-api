"""Consistent API exception responses."""
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Return DRF errors in a consistent response shape."""
    response = exception_handler(exc, context)

    if response is None:
        return None

    response.data = {
        "status": "error",
        "code": response.status_code,
        "errors": response.data,
    }
    return response
