import datetime
import re
import time
from functools import wraps

KST = datetime.timezone(datetime.timedelta(hours=9))

def get_now():
    """현재 시간을 KST 기준으로 반환합니다."""
    return datetime.datetime.now(KST)

def ttl_cache(seconds: int = 60):
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                val, expiry = cache[key]
                if time.time() < expiry:
                    return val
            result = func(*args, **kwargs)
            cache[key] = (result, time.time() + seconds)
            return result
        wrapper.clear = lambda: cache.clear()
        return wrapper
    return decorator

def safe_filename(title: str) -> str:
    """공백을 밑줄로 바꾸고 특수문자를 제거하여 안전한 파일명을 만듭니다."""
    s = str(title).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def slugify(text: str) -> str:
    text = str(text).strip().lower()
    text = text.replace(" ", "-").replace("_", "-")
    text = re.sub(r"[^a-z0-9가-힣\-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")