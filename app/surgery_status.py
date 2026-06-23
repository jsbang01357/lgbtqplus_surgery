from datetime import date, timedelta
from typing import Dict, Any, List
from app.core_utils import get_now

def compute_case_status(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes status, status_auto, missing_items, is_lab_valid, and days_until_surgery for a surgery case.
    
    Status logic:
    - Cancelled cases -> 취소
    - Today's surgery -> 진행중
    - Surgery within 14 days with missing required prep -> 확인필요
    - Missing lab date -> 확인필요
    - Lab date older than 8 weeks before surgery date -> 확인필요
    - Missing anesthesia evaluation, admission confirmation, consent, preop instruction, fasting instruction -> 확인필요 (if within 14 days)
    - Calendar status 미연동 or 오류 -> 확인필요
    - Otherwise 준비완료
    """
    res = dict(case)
    
    is_cancelled = res.get("is_cancelled", False)
    calendar_status = res.get("calendar_status", "미연동")
    
    surgery_date_str = res.get("surgery_date")
    today = get_now().date()
    
    # Parse surgery date safely
    surgery_date = None
    if surgery_date_str:
        try:
            surgery_date = date.fromisoformat(surgery_date_str)
        except (ValueError, TypeError):
            pass
            
    # Get prep dictionary
    prep = res.get("prep")
    if not isinstance(prep, dict):
        prep = {}
    res["prep"] = prep
            
    # Parse lab date safely
    lab_date_str = prep.get("lab_date")
    lab_date = None
    if lab_date_str:
        try:
            lab_date = date.fromisoformat(lab_date_str)
        except (ValueError, TypeError):
            pass

    missing_items: List[str] = []
    
    # Priority 1: Cancelled
    if is_cancelled:
        res["status"] = "취소"
        res["status_auto"] = "취소"
        res["missing_items"] = []
        res["days_until_surgery"] = (surgery_date - today).days if surgery_date else None
        res["is_lab_valid"] = True if lab_date_str else False
        return res
        
    # Priority 2: Today's surgery
    if surgery_date and surgery_date == today:
        res["status"] = "진행중"
        res["status_auto"] = "진행중"
        res["missing_items"] = []
        res["days_until_surgery"] = 0
        res["is_lab_valid"] = True if lab_date_str else False
        return res

    # Compute missing items/warning flags
    is_warning = False

    # Calendar check
    if calendar_status in ("미연동", "오류"):
        is_warning = True
        missing_items.append(f"캘린더 {calendar_status}")

    # Lab date check
    if not lab_date_str:
        is_warning = True
        missing_items.append("검사일 누락")
    elif lab_date and surgery_date:
        # Lab date older than 8 weeks before surgery date
        if (surgery_date - lab_date) > timedelta(weeks=8):
            is_warning = True
            missing_items.append("검사의뢰 8주 초과")

    # Required prep checks
    anesthesia_eval_done = prep.get("anesthesia_eval_done", False)
    admission_confirmed = prep.get("admission_confirmed", False)
    consent_done = prep.get("consent_done", False)
    preop_instruction_done = prep.get("preop_instruction_done", False)
    fasting_instruction_done = prep.get("fasting_instruction_done", False)

    is_within_14_days = False
    if surgery_date:
        is_within_14_days = (surgery_date - today).days <= 14

    # Evaluate required preps matching requirements doc Korean labels
    if not anesthesia_eval_done:
        missing_items.append("마취평가 미완료")
        if is_within_14_days:
            is_warning = True
            
    if not admission_confirmed:
        missing_items.append("입원 여부 미정")
        if is_within_14_days:
            is_warning = True
            
    if not consent_done:
        missing_items.append("동의서 미완료")
        if is_within_14_days:
            is_warning = True
            
    if not preop_instruction_done:
        missing_items.append("수술 전 설명 미완료")
        if is_within_14_days:
            is_warning = True
            
    if not fasting_instruction_done:
        missing_items.append("금식 안내 미완료")
        if is_within_14_days:
            is_warning = True

    if is_warning:
        res["status"] = "확인필요"
        res["status_auto"] = "확인필요"
    else:
        res["status"] = "준비완료"
        res["status_auto"] = "준비완료"
        
    res["missing_items"] = missing_items
    
    # Computed fields
    if surgery_date:
        res["days_until_surgery"] = (surgery_date - today).days
    else:
        res["days_until_surgery"] = None
        
    if lab_date_str and not (lab_date and surgery_date and (surgery_date - lab_date) > timedelta(weeks=8)):
        res["is_lab_valid"] = True
    else:
        res["is_lab_valid"] = False
        
    return res
