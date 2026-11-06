"""Local browser grant boundary; no CORS or unauthenticated computer dispatch."""
import hmac
import secrets
from urllib.parse import urlsplit

_TOKEN = secrets.token_urlsafe(32)


def local_request(environ):
    host = environ.get('HTTP_HOST', '')
    parsed = urlsplit('http://' + host)
    if parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.username or parsed.password or parsed.path:
        raise ValueError('Computer access requires a local application address.')
    origin = environ.get('HTTP_ORIGIN')
    if origin and origin not in {'http://' + host, 'https://' + host}:
        raise ValueError('Computer access requires the application origin.')
    if environ.get('HTTP_SEC_FETCH_SITE') == 'cross-site':
        raise ValueError('Cross-site computer access is not allowed.')


def capabilities(environ):
    local_request(environ)
    import shutil
    return {'available': bool(shutil.which('codex')), 'session_token': _TOKEN,
            'modes': ['project', 'full'], 'browser_control': False}


def require_grant(environ):
    local_request(environ)
    supplied = environ.get('HTTP_X_VIBE_COMPUTER_TOKEN', '')
    if not hmac.compare_digest(supplied, _TOKEN):
        raise ValueError('Refresh computer access in the local application before approving or running.')
