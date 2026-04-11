import datetime
import re
import os
import json
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

KST = datetime.timezone(datetime.timedelta(hours=9))

def get_now():
    """현재 시간을 KST 기준으로 반환합니다."""
    return datetime.datetime.now(KST)

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

@st.cache_resource
def get_gcs_client() -> storage.Client:
    # 1) 환경변수에 서비스계정 JSON 문자열이 있으면 그걸 사용
    sa_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=credentials, project=info["project_id"])

    # 2) Streamlit secrets가 있으면 그걸 사용
    try:
        info = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=credentials, project=info["project_id"])
    except Exception:
        pass

    # 3) 마지막 fallback: Cloud Run ADC 사용
    return storage.Client()


def get_bucket_name() -> str:
    # Cloud Run 환경변수 우선
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if bucket_name:
        return bucket_name

    # Streamlit secrets fallback
    try:
        return st.secrets["gcs"]["bucket_name"]
    except Exception:
        return ""


def get_bucket():
    client = get_gcs_client()
    return client.bucket(get_bucket_name())

def get_blob_mtime(blob_name):
    """GCS 블롭의 수정 시간을 반환합니다."""
    try:
        bucket = get_bucket()
        blob = bucket.get_blob(blob_name)
        if blob and blob.updated:
            return blob.updated.timestamp()
    except Exception:
        pass
    return 0

