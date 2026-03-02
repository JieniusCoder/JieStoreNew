"""
Middleware to log full tracebacks for 500 errors (shows in Render logs).
"""
import logging
import traceback

logger = logging.getLogger(__name__)


class Log500Middleware:
    """Log full traceback when an unhandled exception occurs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.exception(
            "Unhandled exception: %s\n%s",
            exception,
            traceback.format_exc(),
        )
        return None
