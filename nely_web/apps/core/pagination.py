# apps/core/pagination.py
from rest_framework.pagination import PageNumberPagination
from apps.core.response_utils import APIResponse

class CustomPagination(PageNumberPagination):
    page_size = 24  # default, override in settings or per-view

    def get_paginated_response(self, data):
        # Build the same shape DRF uses, but wrap with your APIResponse
        paged = {
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        }
        return APIResponse.success(
            data=paged,
            message="Paginated results"
        )
