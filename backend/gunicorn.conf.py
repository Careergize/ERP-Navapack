"""Portable Linux process config; TLS terminates at a reviewed trusted ingress."""
import os

bind = '0.0.0.0:' + os.getenv('PORT', '8000')
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
worker_class = 'gthread'
threads = int(os.getenv('GUNICORN_THREADS', '2'))
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
errorlog = '-'
# API middleware logs method/status/request ID without bodies, headers or query data.
accesslog = None
capture_output = True
forwarded_allow_ips = os.getenv('FORWARDED_ALLOW_IPS', '127.0.0.1,::1')
