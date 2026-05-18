import json
import logging
from app.core_utils import get_now
from app.gcs_helper import get_bucket, get_logs_blob_name
from app.request_utils import get_client_ip

MAX_LOGS = 500
logger = logging.getLogger(__name__)

def log_access_request(headers: dict, client_ip: str = None):
    """접속 기록을 누적하여 GCS에 저장합니다. (동시성 보호 적용)"""
    ip = client_ip or get_client_ip(headers)
    ua = headers.get("user-agent") or headers.get("User-Agent", "Unknown Browser")
    
    new_entry = {
        "time": get_now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "ua": ua
    }

    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())

    # 최대 5회 재시도 (동시성 충돌 시)
    for _ in range(5):
        logs = []
        generation = 0
        if blob.exists():
            try:
                blob.reload()
                generation = blob.generation
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                if isinstance(data, list):
                    logs = data
                elif isinstance(data, dict):
                    if "last_access" in data:
                        logs = [{"time": data["last_access"], "ip": "Unknown", "ua": "Old Record"}]
            except Exception:
                logs = []
        
        # 새로운 로그를 앞에 추가 및 개수 제한
        logs.insert(0, new_entry)
        logs = logs[:MAX_LOGS]

        try:
            blob.upload_from_string(
                json.dumps(logs, ensure_ascii=False, indent=2),
                content_type="application/json; charset=utf-8",
                if_generation_match=generation
            )
            return True
        except Exception:
            # generation mismatch or other GCS error, retry
            continue
    
    logger.warning("접속 로그 저장에 실패했습니다 (동시성 충돌).")
    return False

def log_access():
    """Streamlit 호환용 접속 기록 저장 함수 (필요 시 유지)"""
    try:
        import streamlit as st
        if "access_logged" in st.session_state:
            return
        
        success = log_access_request(st.context.headers)
        if success:
            st.session_state.access_logged = True
    except Exception:
        pass

def get_access_logs():
    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())

    if not blob.exists():
        return []

    try:
        raw = blob.download_as_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return []

def save_access_logs(logs):
    """(주의) 이 함수는 generation 체크 없이 덮어씁니다. 가급적 log_access_request를 쓰세요."""
    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())
    blob.upload_from_string(
        json.dumps(logs[:MAX_LOGS], ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )

def clear_access_logs():
    """접속 기록을 모두 삭제합니다."""
    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())
    if blob.exists():
        try:
            blob.delete()
        except Exception:
            logger.exception("접속 로그 삭제에 실패했습니다.")
