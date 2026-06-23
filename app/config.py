import os
import logging

logger = logging.getLogger(__name__)


def _load_dotenv():
    values = {}
    path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(path):
        return values

    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                values[key] = value
    except Exception:
        logger.warning(".env 로드에 실패했습니다.", exc_info=True)
    return values


def _load_secrets_toml():
    try:
        import tomllib
        path = os.path.join(".streamlit", "secrets.toml")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return tomllib.load(f)
    except Exception:
        logger.warning("secrets.toml 로드에 실패했습니다.", exc_info=True)
    return {}

_DOTENV_CACHE = None
_SECRETS_CACHE = None

def get_config(key: str, default: str = "") -> str:
    global _DOTENV_CACHE, _SECRETS_CACHE
    # 1. Environment Variable
    value = os.getenv(key)
    if value:
        return value

    # 2. Local .env file for offline/Mac mini operation
    if _DOTENV_CACHE is None:
        _DOTENV_CACHE = _load_dotenv()

    if key in _DOTENV_CACHE:
        return str(_DOTENV_CACHE[key])

    for k, v in _DOTENV_CACHE.items():
        if k.lower() == key.lower():
            return str(v)

    # 3. Direct TOML reading for uvicorn/bare context
    if _SECRETS_CACHE is None:
        _SECRETS_CACHE = _load_secrets_toml()
    
    # Try exact match first
    if key in _SECRETS_CACHE:
        return str(_SECRETS_CACHE[key])

    # Try case-insensitive top-level match
    for k, v in _SECRETS_CACHE.items():
        if k.lower() == key.lower() and not isinstance(v, dict):
            return str(v)
    
    # Section check
    for section_name, section in _SECRETS_CACHE.items():
        if isinstance(section, dict):
            # Try exact match or case-insensitive match inside section
            for k, v in section.items():
                if k.lower() == key.lower():
                    return str(v)
            
            # Case 2: key starts with section_name + "_"
            if key.lower().startswith(section_name.lower() + "_"):
                short_key = key.lower()[len(section_name) + 1 :]
                for k, v in section.items():
                    if k.lower() == short_key:
                        return str(v)

    return default

def get_secrets_dict() -> dict:
    global _SECRETS_CACHE
    if _SECRETS_CACHE is None:
        _SECRETS_CACHE = _load_secrets_toml()
    
    combined = dict(_SECRETS_CACHE)

    return combined

def get_admin_password() -> str:
    return get_config("ADMIN_PASSWORD", "")

def get_gemini_api_key() -> str:
    return get_config("GEMINI_API_KEY", "")

def get_bucket_name() -> str:
    return get_config("GCS_BUCKET_NAME", "lgbtqplus-surgery")


def get_storage_backend() -> str:
    return get_config("STORAGE_BACKEND", "gcs").strip().lower()


def get_local_storage_root() -> str:
    return get_config("LOCAL_STORAGE_ROOT", ".local_data/storage")


def get_gdrive_folder_id() -> str:
    return get_config("GDRIVE_FOLDER_ID", "1CwDmMwubRla-8NbbKKXgQOoEvzxuMKzF")


def get_gdrive_oauth_config() -> dict:
    return {
        "client_id": get_config("GDRIVE_CLIENT_ID", ""),
        "client_secret": get_config("GDRIVE_CLIENT_SECRET", ""),
        "redirect_uri": get_config("GDRIVE_REDIRECT_URI", "http://localhost:8080/api/auth/gdrive/callback"),
    }


def get_bool_config(key: str, default: bool = False) -> bool:
    raw = get_config(key, "")
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_int_config(key: str, default: int) -> int:
    raw = get_config(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def allow_public_registration() -> bool:
    return get_bool_config("ALLOW_PUBLIC_REGISTRATION", False)


def offline_mode() -> bool:
    local_backend = get_storage_backend() in {"local", "file", "filesystem", "offline"}
    return get_bool_config("OFFLINE_MODE", local_backend)


def google_calendar_sync_enabled() -> bool:
    return get_bool_config("GOOGLE_CALENDAR_SYNC_ENABLED", not offline_mode())
