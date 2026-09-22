import logging


logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    'access_token', 'refresh_token', 'client_secret', 'password',
    'passport_number', 'passport_pin', 'passportpin', 'hash', 'hash2',
    'token', 'secret',
}


def _redact(value):
    if isinstance(value, dict):
        return {
            str(key): _redact(item)
            for key, item in value.items()
            if str(key).lower() not in _SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def safe_log_data(data, action):
    """Faqat maxfiy qiymatlarsiz metadata loglaydi; raw payload yozmaydi."""
    sanitized = _redact(data)
    keys = sorted(sanitized.keys()) if isinstance(sanitized, dict) else []
    logger.info("%s: HEMIS payload qabul qilindi (keys=%s)", action, keys)
    return sanitized
