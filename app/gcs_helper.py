import os
import json
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account


@st.cache_resource
def get_gcs_client() -> storage.Client:
    """
    우선순위:
    1) GCP_SERVICE_ACCOUNT_JSON 환경변수
    2) Streamlit secrets
    3) Cloud Run ADC
    """
    sa_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=credentials, project=info["project_id"])

    try:
        info = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=credentials, project=info["project_id"])
    except Exception:
        pass

    # Cloud Run에서는 런타임 서비스 계정의 ADC 사용
    return storage.Client()


def get_bucket_name() -> str:
    """
    우선순위:
    1) GCS_BUCKET_NAME 환경변수
    2) Streamlit secrets
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if bucket_name:
        return bucket_name

    try:
        gcs_section = st.secrets["gcs"]
        if "bucket_name" in gcs_section and gcs_section["bucket_name"]:
            return gcs_section["bucket_name"]
    except Exception:
        pass

    raise RuntimeError(
        "GCS bucket name is not configured. "
        "Set GCS_BUCKET_NAME in Cloud Run environment variables "
        "or provide gcs.bucket_name in Streamlit secrets."
    )


def get_bucket() -> storage.Bucket:
    return get_gcs_client().bucket(get_bucket_name())


def get_logs_blob_name() -> str:
    return "logs/access_log.json"
