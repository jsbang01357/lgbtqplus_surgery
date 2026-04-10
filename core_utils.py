import datetime
import re
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

def get_gcs_client() -> storage.Client:
    """Streamlit secrets에서 인증 정보를 읽어 GCS 클라이언트를 반환합니다."""
    info = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials, project=info["project_id"])

def get_bucket():
    """설정된 GCS 버킷 객체를 반환합니다."""
    client = get_gcs_client()
    bucket_name = st.secrets["gcs"]["bucket_name"]
    return client.bucket(bucket_name)

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

