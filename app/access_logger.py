import streamlit as st
import json
from app.core_utils import get_now
from app.gcs_helper import get_bucket, get_logs_blob_name

ACCESS_LOG_BLOB = "logs/access_log.json"
MAX_LOGS = 500

def get_visitor_info():
    """방문자의 IP와 브라우저 정보를 가져옵니다."""
    try:
        # Streamlit 1.34+ headers
        headers = st.context.headers
        
        # IP 추출 (프록시 고려)
        ip = headers.get("X-Forwarded-For")
        if ip:
            ip = ip.split(",")[0].strip()
        else:
            ip = headers.get("Remote-Addr", "Unknown")
            
        # 브라우저 정보 추출
        ua = headers.get("User-Agent", "Unknown Browser")
        return ip, ua
    except Exception:
        return "Unknown IP", "Unknown Browser"

def log_access():
    """접속 기록을 누적하여 GCS에 저장합니다."""
    # 세션당 한 번만 기록 (새로고침 시 중복 기록 방지)
    if "access_logged" in st.session_state:
        return
    
    bucket = get_bucket()
    blob = bucket.blob(ACCESS_LOG_BLOB)
    
    logs = []
    if blob.exists():
        try:
            data = json.loads(blob.download_as_text(encoding="utf-8"))
            if isinstance(data, list):
                logs = data
            elif isinstance(data, dict):
                # 구버전 호환성: 단일 dict를 리스트로 변환
                if "last_access" in data:
                    logs = [{"time": data["last_access"], "ip": "Unknown", "ua": "Old Record"}]
        except Exception:
            logs = []

    ip, ua = get_visitor_info()
    new_entry = {
        "time": get_now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "ua": ua
    }
    
    # 새로운 로그를 앞에 추가
    logs.insert(0, new_entry)
    
    # 최대 개수(500개) 유지
    logs = logs[:MAX_LOGS]
    
    try:
        blob.upload_from_string(
            json.dumps(logs, ensure_ascii=False, indent=2),
            content_type="application/json"
        )
        st.session_state.access_logged = True
        # 화면 표시용 최신 기록 저장
        st.session_state.last_access_display = new_entry["time"]
    except Exception as e:
        print(f"Logging error: {e}")




def get_access_logs():
    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())

    if not blob.exists():
        return []

    raw = blob.download_as_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_access_logs(logs):
    bucket = get_bucket()
    blob = bucket.blob(get_logs_blob_name())
    blob.upload_from_string(
        json.dumps(logs, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )

def clear_access_logs():
    """접속 기록을 모두 삭제합니다."""
    bucket = get_bucket()
    blob = bucket.blob(ACCESS_LOG_BLOB)
    if blob.exists():
        blob.delete()
    
    if "last_access_display" in st.session_state:
        st.session_state.last_access_display = "기본 없음"
