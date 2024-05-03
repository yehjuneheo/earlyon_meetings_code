# myapp/middleware.py
from django.http import HttpResponse
import re

class MobileDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        mobile_browser_patterns = [
            'mobile', 'opera mini', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'
        ]

        if any(pattern in user_agent for pattern in mobile_browser_patterns):
            # This is a simple response, you could also set a flag in the session
            # and handle it in your views to show a tailored warning message.
            return HttpResponse("This website is optimized for desktop usage and does not fully support mobile devices.", status=403)

        response = self.get_response(request)
        return response
