import os

def get_config(key: str, default: str = "") -> str:
    # 1. Environment Variable
    value = os.getenv(key)
    if value:
        return value

    # 2. Local fallback or Streamlit secrets (for legacy compatibility)
    # Note: st.secrets will fail if not in Streamlit, so we try-catch it
    try:
        import streamlit as st
        # Flattened access for simplicity
        if key.lower() in st.secrets:
            return str(st.secrets[key.lower()])
        # Nested access (e.g., st.secrets["admin"]["admin_password"])
        for section in st.secrets.values():
            if isinstance(section, dict) and key.lower() in section:
                return str(section[key.lower()])
    except (ImportError, Exception):
        pass

    return default

def get_admin_password() -> str:
    return get_config("ADMIN_PASSWORD", "cbd_07079")

def get_gemini_api_key() -> str:
    return get_config("GEMINI_API_KEY", "")

def get_bucket_name() -> str:
    return get_config("GCS_BUCKET_NAME", "jisong-cloud-storage")
