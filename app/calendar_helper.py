import json
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gcs_helper import get_bucket
import os

logger = logging.getLogger(__name__)

GDRIVE_TOKEN_BLOB = "auth/gdrive_token.json"

def get_calendar_service():
    try:
        bucket = get_bucket()
        blob = bucket.blob(GDRIVE_TOKEN_BLOB)
        if not blob.exists():
            return None
        
        token_data = json.loads(blob.download_as_text(encoding="utf-8"))
        creds = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
        
        # Build calendar resource with static analysis type ignore
        service = build("calendar", "v3", credentials=creds, static_discovery=False) # type: ignore
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Google Calendar service: {e}")
        return None

def sync_case_to_calendar(case: dict) -> dict:
    """
    Syncs a surgery case to Google Calendar.
    If the case has calendar_event_id, it updates the existing event.
    Otherwise, it creates a new event.
    Returns the updated case dict with calendar_status, calendar_event_id, and calendar_error.
    """
    res = dict(case)
    
    service = get_calendar_service()
    if not service:
        res["calendar_status"] = "미연동"
        res["calendar_event_id"] = ""
        res["calendar_error"] = ""
        return res
        
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    event_id = res.get("calendar_event_id")
    
    # State flags
    is_cancelled = res.get("is_cancelled", False) or res.get("surgery_status") == "취소"
    surgery_status = res.get("surgery_status", "예정")
    
    # Format Title
    prefix = "[확정] "
    if is_cancelled:
        prefix = "[취소] "
    elif surgery_status == "가예약":
        prefix = "[가예약] "
        
    pat_code = res.get("patient_code") or ""
    summary = f"{prefix}{pat_code} / {res.get('surgery_name')} / {res.get('surgeon')}"
    
    # Preop computed status
    from app.surgery_status import compute_case_status
    computed = compute_case_status(res)
    missing_str = ", ".join(computed.get("missing_items", [])) or "없음"
    
    # Build detailed description
    description = f"""환자코드: {pat_code}
수술명: {res.get('surgery_name')}
집도의: {res.get('surgeon')}
수술방: {res.get('operating_room')}
마취: {res.get('anesthesia')}
준비상태: {computed.get('status_auto')}
누락항목: {missing_str}"""

    event_body = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': f"{res.get('surgery_date')}T{res.get('surgery_start_time')}:00",
            'timeZone': 'Asia/Seoul',
        },
        'end': {
            'dateTime': f"{res.get('surgery_date')}T{res.get('surgery_end_time')}:00",
            'timeZone': 'Asia/Seoul',
        },
    }

    try:
        if is_cancelled:
            if event_id:
                service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute() # type: ignore
                res["calendar_status"] = "연동완료"
                res["calendar_error"] = ""
            else:
                created = service.events().insert(calendarId=calendar_id, body=event_body).execute() # type: ignore
                res["calendar_event_id"] = created.get("id")
                res["calendar_status"] = "연동완료"
                res["calendar_error"] = ""
        else:
            if event_id:
                try:
                    service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute() # type: ignore
                    res["calendar_status"] = "연동완료"
                    res["calendar_error"] = ""
                except Exception as update_err:
                    if "404" in str(update_err) or "notFound" in str(update_err):
                        created = service.events().insert(calendarId=calendar_id, body=event_body).execute() # type: ignore
                        res["calendar_event_id"] = created.get("id")
                        res["calendar_status"] = "연동완료"
                        res["calendar_error"] = ""
                    else:
                        raise update_err
            else:
                created = service.events().insert(calendarId=calendar_id, body=event_body).execute() # type: ignore
                res["calendar_event_id"] = created.get("id")
                res["calendar_status"] = "연동완료"
                res["calendar_error"] = ""
    except Exception as e:
        logger.error(f"Google Calendar sync error: {e}")
        res["calendar_status"] = "오류"
        res["calendar_error"] = str(e)
        
    return res

def delete_calendar_event_safe(event_id: str):
    if not event_id:
        return
    service = get_calendar_service()
    if not service:
        return
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute() # type: ignore
    except Exception as e:
        logger.error(f"Failed to delete Google Calendar event {event_id}: {e}")
