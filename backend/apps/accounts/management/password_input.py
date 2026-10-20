import getpass
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError


def read_validated_password(user):
    try:
        first=getpass.getpass('New password: ')
        second=getpass.getpass('Confirm password: ')
    except (EOFError,KeyboardInterrupt):
        raise CommandError('A secure interactive password prompt is required.')
    if first != second: raise CommandError('Passwords do not match.')
    try: validate_password(first,user=user)
    except ValidationError as exc: raise CommandError('; '.join(exc.messages))
    return first
