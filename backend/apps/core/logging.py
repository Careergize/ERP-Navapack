import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Fixed messages only: Django may otherwise embed exception/URL/user data.
        data = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': record.levelname,
                'logger': record.name, 'message': 'request_error' if record.name.startswith('django') else record.getMessage()}
        for key in ('request_id', 'status_code', 'method', 'actor_id', 'action', 'outcome'):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data)
