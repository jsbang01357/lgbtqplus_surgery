import os
import json
from google.cloud import storage
from google.oauth2 import service_account
from app.config import get_config, get_bucket_name as config_bucket_name

_GCS_CLIENT_CACHE = None

def get_gcs_client() -> storage.Client:
    global _GCS_CLIENT_CACHE
    if _GCS_CLIENT_CACHE is not None:
        return _GCS_CLIENT_CACHE

    sa_json = get_config("GCP_SERVICE_ACCOUNT_JSON")
    if sa_json:
        try:
            info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            _GCS_CLIENT_CACHE = storage.Client(credentials=credentials, project=info["project_id"])
            return _GCS_CLIENT_CACHE
        except Exception:
            pass

    # Cloud Run/ADC
    _GCS_CLIENT_CACHE = storage.Client()
    return _GCS_CLIENT_CACHE


def get_bucket_name() -> str:
    bucket_name = config_bucket_name()
    if bucket_name:
        return bucket_name

    raise RuntimeError("GCS bucket name is not configured.")


def get_bucket() -> storage.Bucket:
    return get_gcs_client().bucket(get_bucket_name())


def get_logs_blob_name() -> str:
    return "logs/access_log.json"
