import os
import logging

logger = logging.getLogger(__name__)

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

_SECRETS_CACHE = None

def get_config(key: str, default: str = "") -> str:
    global _SECRETS_CACHE
    # 1. Environment Variable
    value = os.getenv(key)
    if value:
        return value

    # 2. Local fallback or Streamlit secrets
    try:
        import streamlit as st
        # If we are in streamlit context, use st.secrets
        if hasattr(st, "secrets") and st.secrets:
            if key.lower() in st.secrets:
                return str(st.secrets[key.lower()])
            for section in st.secrets.values():
                if isinstance(section, dict) and key.lower() in section:
                    return str(section[key.lower()])
    except ImportError:
        pass
    except Exception:
        logger.warning("Streamlit secrets 로드에 실패했습니다.", exc_info=True)

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
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            for k, v in st.secrets.items():
                if isinstance(v, dict):
                    combined[k] = {**combined.get(k, {}), **v}
                else:
                    combined[k] = v
    except ImportError:
        pass
    except Exception:
        logger.warning("Streamlit secrets dictionary 병합에 실패했습니다.", exc_info=True)
    return combined

def get_admin_password() -> str:
    return get_config("ADMIN_PASSWORD", "")

def get_gemini_api_key() -> str:
    return get_config("GEMINI_API_KEY", "")

def get_bucket_name() -> str:
    return get_config("GCS_BUCKET_NAME", "jisong-cloud-storage")


def get_gdrive_folder_id() -> str:
    return get_config("GDRIVE_FOLDER_ID", "1CwDmMwubRla-8NbbKKXgQOoEvzxuMKzF")


def get_bool_config(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
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
