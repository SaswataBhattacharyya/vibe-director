"""Local request checks and secret-free capability discovery. Consent is native."""
from urllib.parse import urlsplit


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
    return {'available': bool(shutil.which('codex')), 'authorization': 'native-per-operation',
            'native_confirmation_available': bool(shutil.which('zenity')),
            'modes': ['project', 'full'], 'browser_control': False}
