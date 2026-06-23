from datetime import date, timedelta
from typing import Dict, Any, List
from app.core_utils import get_now

def compute_case_status(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes status, status_auto, missing_items, is_lab_valid, and days_until_surgery for a surgery case.
    
    Status logic:
    - Cancelled cases (is_cancelled=True or surgery_status="취소") -> 취소
    - Today's surgery -> 진행중
    - Warning criteria (immediate confirmation required):
        - Missing lab date (no lab_date and no lab_completed_date) -> 확인필요
        - Lab date is more than 8 weeks (56 days) before the surgery date -> 확인필요
        - Calendar status is "오류" -> 확인필요
    - Warning criteria (within 14 days of surgery):
        - premed_status is not "완료" (is "미완료" or empty) -> 확인필요
        - cooperation_status is not "완료" and not "불필요" -> 확인필요
        - admission_guidance_done is False -> 확인필요
        - documents_checked is False -> 확인필요
    - Otherwise -> 준비완료
    """
    res = dict(case)
    
    is_cancelled = res.get("is_cancelled", False) or res.get("surgery_status") == "취소"
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
    
    # Check lab date
    # Priority: lab_completed_date -> lab_date
    lab_date_str = prep.get("lab_completed_date") or prep.get("lab_date")
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

    is_warning = False

    # Immediate warnings (independent of D-day)
    if calendar_status == "오류":
        is_warning = True
        missing_items.append("캘린더 연동 오류")

    if not lab_date_str:
        is_warning = True
        missing_items.append("검사일 누락")
    elif lab_date and surgery_date:
        if (surgery_date - lab_date) > timedelta(weeks=8):
            is_warning = True
            missing_items.append("검사의뢰 8주 초과")

    # Required prep checks (warnings are active if surgery is within 14 days)
    premed_status = prep.get("premed_status", "미완료")
    cooperation_status = prep.get("cooperation_status", "불필요")
    admission_guidance_done = prep.get("admission_guidance_done", False)
    documents_checked = prep.get("documents_checked", False)

    is_within_14_days = False
    if surgery_date:
        is_within_14_days = (surgery_date - today).days <= 14

    # Premed check
    if premed_status != "완료":
        missing_items.append("프리메드 미완료")
        if is_within_14_days and premed_status != "불필요":
            is_warning = True
            
    # Cooperation check
    if cooperation_status not in ("완료", "불필요"):
        missing_items.append(f"협진 {cooperation_status}")
        if is_within_14_days:
            is_warning = True
            
    # Admission guidance check
    if not admission_guidance_done:
        missing_items.append("입원안내 미완료")
        if is_within_14_days:
            is_warning = True
            
    # Documents checked check
    if not documents_checked:
        missing_items.append("서류확인 미완료")
        if is_within_14_days:
            is_warning = True

    # Map state status
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
