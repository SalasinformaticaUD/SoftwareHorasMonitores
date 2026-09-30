from rest_framework.pagination import PageNumberPagination


class OptionalPageNumberPagination(PageNumberPagination):
    """Paginate only when the client explicitly asks for a page.

    Keeping the legacy array response for existing consumers lets the web
    application migrate module by module, while new list views avoid loading
    an entire semester in one request.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)
