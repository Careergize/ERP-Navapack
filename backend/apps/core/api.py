import logging
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommandConflict(APIException):
    status_code = 409
    default_code = 'idempotency_conflict'
    default_detail = 'This command key was already used with another payload.'


class StaleReview(CommandConflict):
    default_code = 'stale_review'
    default_detail = 'The reviewed plan is stale; review again.'


class PreconditionRequired(APIException):
    status_code = 428
    default_code = 'version_required'
    default_detail = 'A quoted integer If-Match version is required.'


class VersionConflict(APIException):
    status_code = 412
    default_code = 'version_conflict'
    default_detail = 'The resource version has changed.'


def error_body(code, message, request_id, fields=None, details=None):
    return {'error': {'code': code, 'message': message, 'fields': fields or {},
                      'details': details or {}, 'request_id': str(request_id)}}


def exception_handler(exc, context):
    request = context.get('request')
    request_id = getattr(request, 'request_id', '')
    response = drf_exception_handler(exc, context)
    if response is None:
        # Do not log exception text, request payloads, tokens or SQL parameters.
        logging.getLogger('api').error('Unhandled API error', extra={'request_id': str(request_id)})
        return Response(error_body('internal_error', 'An internal error occurred.', request_id), status=500)
    codes = getattr(exc, 'get_codes', lambda: 'request_error')()
    if isinstance(exc, ValidationError):
        code, message, fields = 'validation_error', 'Invalid input.', response.data
    else:
        code = codes if isinstance(codes, str) else getattr(exc, 'default_code', 'request_error')
        message = str(response.data.get('detail', 'Request failed.'))
        fields = {}
    response.data = error_body(code, message, request_id, fields)
    return response
