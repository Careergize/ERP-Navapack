import logging
import uuid
from django.http import JsonResponse
from .api import error_body


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            request.request_id = uuid.UUID(request.headers.get('X-Request-ID', ''))
        except (ValueError, TypeError, AttributeError):
            request.request_id = uuid.uuid4()
        response = self.get_response(request)
        if request.path.startswith('/api/') and response.status_code >= 400 and 'application/json' not in response.get('Content-Type', ''):
            codes = {400: 'bad_request', 403: 'permission_denied', 404: 'not_found', 405: 'method_not_allowed'}
            response = JsonResponse(error_body(codes.get(response.status_code, 'internal_error'),
                'Request failed.', request.request_id), status=response.status_code)
        response['X-Request-ID'] = str(request.request_id)
        if request.path.startswith('/api/v1/auth/'):
            response['Cache-Control'] = 'no-store'
            response['Pragma'] = 'no-cache'
        logging.getLogger('api.request').info('API request completed', extra={
            'request_id': str(request.request_id), 'status_code': response.status_code,
            'method': request.method})
        return response
