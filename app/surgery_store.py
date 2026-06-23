import json
import logging
import uuid
from typing import Dict, Any, List, Optional

from app.gcs_helper import get_bucket
from app.core_utils import get_now, ttl_cache
from app.surgery_status import compute_case_status

logger = logging.getLogger(__name__)

CASES_PREFIX = "surgery_ops/cases"
AUDIT_LOG_BLOB = "surgery_ops/audit/surgery_ops_audit.jsonl"


def clear_surgery_cache():
    clear_cases = getattr(get_cases_cached, "clear", None)
    if clear_cases:
        clear_cases()
    clear_case = getattr(get_case_cached, "clear", None)
    if clear_case:
        clear_case()


@ttl_cache(seconds=5)
def get_cases_cached() -> List[Dict[str, Any]]:
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix=f"{CASES_PREFIX}/")
    cases = []
    
    for blob in blobs:
        if blob.name.endswith("/") or not blob.name.endswith(".json"):
            continue
            
        try:
            content = blob.download_as_text(encoding="utf-8")
            case_data = json.loads(content)
            # Recompute status on read
            cases.append(compute_case_status(case_data))
        except Exception as e:
            logger.error(f"Error loading surgery case blob {blob.name}: {e}")
            
    return cases


def get_cases() -> List[Dict[str, Any]]:
    return get_cases_cached()


@ttl_cache(seconds=5)
def get_case_cached(case_id: str) -> Optional[Dict[str, Any]]:
    bucket = get_bucket()
    blob = bucket.blob(f"{CASES_PREFIX}/{case_id}.json")
    if not blob.exists():
        return None
        
    try:
        content = blob.download_as_text(encoding="utf-8")
        case_data = json.loads(content)
        return compute_case_status(case_data)
    except Exception as e:
        logger.error(f"Error loading surgery case {case_id}: {e}")
        return None


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    return get_case_cached(case_id)


def save_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case_data.get("case_id")
    if not case_id:
        case_id = f"case_{uuid.uuid4().hex[:16]}"
        case_data["case_id"] = case_id
        
    now_str = get_now().isoformat()
    if "created_at" not in case_data:
        case_data["created_at"] = now_str
    case_data["updated_at"] = now_str

    # Ensure required default fields are present
    defaults = {
        "patient_name": "",
        "patient_preferred_name": "",
        "notes": "",
        "calendar_status": "미연동",
        "calendar_event_id": "",
        "is_cancelled": False,
        "cancellation_reason": "",
        "diagnosis": "",
        "coop_detail": "",
        "insurance_types": [],
        "surgery_fee": "",
        "surgery_duration": 0,
        "room_type": "",
        "surgery_status": "예정",
        "pending_requester": "",
        "pending_registered_date": "",
        "pending_deadline": "",
        "is_confirmed": False,
        "pending_memo": "",
        "an_call_required": False,
        "an_call_scheduled_date": "",
        "an_call_completed_date": "",
        "an_call_checker": "",
        "an_call_patient_intent": "미정",
        "an_call_notes": "",
        "an_call_followup_needed": False,
        "room_1person_required": False,
        "room_1person_status": "미정",
        "room_memo": "",
        "room_gender_neutral_required": False,
        "room_gender_neutral_consent": False,
        "room_gender_neutral_status": "불필요",
        "room_gender_neutral_checker": "",
        "room_gender_neutral_checked_date": "",
        "coop_status": "불필요",
        "coop_dept": "",
        "coop_doctor": "",
        "coop_notes": "",
        "coop_confirmed": False,
        "coop_memo": "",
    }
    for k, v in defaults.items():
        if k not in case_data:
            case_data[k] = v

    if "prep" not in case_data or not isinstance(case_data["prep"], dict):
        case_data["prep"] = {}
        
    prep_defaults = {
        "lab_date": "",
        "lab_scheduled_date": "",
        "lab_completed_date": "",
        "lab_status": "",
        "anesthesia_eval_done": False,
        "admission_confirmed": False,
        "consent_done": False,
        "preop_instruction_done": False,
        "fasting_instruction_done": False,
        "premed_status": "미완료",
        "cooperation_status": "불필요",
        "admission_guidance_done": False,
        "documents_checked": False,
        "last_checker": "",
        "last_checked_date": "",
        "prep_memo": "",
    }
    for k, v in prep_defaults.items():
        if k not in case_data["prep"]:
            case_data["prep"][k] = v

    if "premed_detail" not in case_data["prep"] or not isinstance(case_data["prep"]["premed_detail"], dict):
        case_data["prep"]["premed_detail"] = {}

    premed_detail_defaults = {
        "writer": "",
        "lab_checker": "",
        "coop_checker": "",
        "amount": "",
        "consent_admission": False,
        "consent_surgery": False,
        "consent_discharge": False,
        "premed_notes": "",
        "history_disease": "",
        "history_disease_year": "",
        "history_med_name": "",
        "history_med_dose": "",
        "history_med_frequency": "",
        "history_med_stop_date": "",
        "history_hormone_med": "",
        "history_hormone_dose": "",
        "history_hormone_period": "",
        "history_surgery_history": "",
        "history_surgery_year": "",
        "history_surgery_hospital": "",
        "history_allergy": "",
        "exam_ekg": "",
        "exam_chest": "",
        "exam_lab_notes": "",
    }
    for k, v in premed_detail_defaults.items():
        if k not in case_data["prep"]["premed_detail"]:
            case_data["prep"]["premed_detail"][k] = v

    # Sync to Google Calendar before uploading to GCS
    try:
        from app.calendar_helper import sync_case_to_calendar
        case_data = sync_case_to_calendar(case_data)
    except Exception as e:
        logger.error(f"Failed to sync case to Google Calendar: {e}")

    bucket = get_bucket()
    blob = bucket.blob(f"{CASES_PREFIX}/{case_id}.json")
    
    # Save raw data without calculated status/missing_items fields to avoid redundancy
    raw_to_save = dict(case_data)
    raw_to_save.pop("status", None)
    raw_to_save.pop("status_auto", None)
    raw_to_save.pop("missing_items", None)
    raw_to_save.pop("days_until_surgery", None)
    raw_to_save.pop("is_lab_valid", None)
    
    blob.upload_from_string(
        json.dumps(raw_to_save, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8"
    )
    
    clear_surgery_cache()
    
    # Audit log
    write_audit_log(
        action="save", 
        case_id=case_id, 
        detail=f"Patient: {case_data.get('patient_code')} / Date: {case_data.get('surgery_date')}"
    )
    
    return compute_case_status(case_data)


def delete_case(case_id: str) -> bool:
    bucket = get_bucket()
    blob = bucket.blob(f"{CASES_PREFIX}/{case_id}.json")
    if blob.exists():
        try:
            content = blob.download_as_text(encoding="utf-8")
            case_data = json.loads(content)
            event_id = case_data.get("calendar_event_id")
            if event_id:
                from app.calendar_helper import delete_calendar_event_safe
                delete_calendar_event_safe(event_id)
        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event for case {case_id}: {e}")

        blob.delete()
        clear_surgery_cache()
        write_audit_log(action="delete", case_id=case_id, detail="Deleted case")
        return True
    return False


def cancel_case(case_id: str, reason: str) -> Optional[Dict[str, Any]]:
    case = get_case(case_id)
    if not case:
        return None
        
    case["is_cancelled"] = True
    case["cancellation_reason"] = reason
    case["updated_at"] = get_now().isoformat()
    
    saved = save_case(case)
    write_audit_log(action="cancel", case_id=case_id, detail=f"Reason: {reason}")
    return saved


def restore_case(case_id: str) -> Optional[Dict[str, Any]]:
    case = get_case(case_id)
    if not case:
        return None
        
    case["is_cancelled"] = False
    case["cancellation_reason"] = ""
    case["updated_at"] = get_now().isoformat()
    
    saved = save_case(case)
    write_audit_log(action="restore", case_id=case_id, detail="Restored case")
    return saved


def write_audit_log(action: str, case_id: str, detail: str):
    try:
        bucket = get_bucket()
        blob = bucket.blob(AUDIT_LOG_BLOB)
        
        current_logs = ""
        if blob.exists():
            current_logs = blob.download_as_text(encoding="utf-8")
            
        log_entry = {
            "timestamp": get_now().isoformat(),
            "action": action,
            "case_id": case_id,
            "detail": detail
        }
        
        new_logs = current_logs.rstrip("\n") + "\n" + json.dumps(log_entry, ensure_ascii=False) + "\n"
        blob.upload_from_string(
            new_logs,
            content_type="application/x-jsonlines; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to write audit log to GCS: {e}")
