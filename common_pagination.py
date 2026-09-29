from rest_framework.pagination import PageNumberPagination


class LargeResultsPagination(PageNumberPagination):
    """Pagination class for search endpoints."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
