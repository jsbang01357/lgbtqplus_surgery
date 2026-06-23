import csv
import io
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.api_deps import get_current_user, _json, _error
from app.surgery_store import (
    get_cases, get_case, save_case, delete_case, cancel_case, restore_case
)
from app.surgery_schema import SurgeryCaseCreate, SurgeryCaseUpdate, SurgeryCancelRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/surgery", tags=["surgery"])


@router.get("/cases")
async def get_all_cases(request: Request, _: bool = Depends(get_current_user)):
    cases = get_cases()
    
    # Sort: status == "확인필요" first, then surgery_date ascending
    def sort_key(c: Dict[str, Any]):
        is_warning = c.get("status") == "확인필요"
        date_val = c.get("surgery_date") or "9999-12-31"
        time_val = c.get("surgery_start_time") or "00:00"
        # True is 1, False is 0. We want warning first, so we use (0 if warning else 1)
        return (0 if is_warning else 1, date_val, time_val)
        
    cases.sort(key=sort_key)
    return _json({"cases": cases})


@router.post("/cases")
async def create_new_case(
    payload: SurgeryCaseCreate, 
    _: bool = Depends(get_current_user)
):
    try:
        saved = save_case(payload.model_dump())
        return _json({"ok": True, "case": saved})
    except Exception as e:
        return _error(f"수술 케이스 생성 실패: {str(e)}", status_code=500)


@router.get("/cases/{case_id}")
async def get_case_detail(
    case_id: str, 
    _: bool = Depends(get_current_user)
):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="수술 일정을 찾을 수 없습니다.")
    return _json({"case": case})


@router.put("/cases/{case_id}")
async def update_existing_case(
    case_id: str, 
    payload: SurgeryCaseUpdate, 
    _: bool = Depends(get_current_user)
):
    existing = get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="수술 일정을 찾을 수 없습니다.")
        
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        existing[k] = v
        
    try:
        saved = save_case(existing)
        return _json({"ok": True, "case": saved})
    except Exception as e:
        return _error(f"수술 케이스 수정 실패: {str(e)}", status_code=500)


@router.delete("/cases/{case_id}")
async def delete_existing_case(
    case_id: str, 
    _: bool = Depends(get_current_user)
):
    success = delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="수술 일정을 찾을 수 없거나 삭제에 실패했습니다.")
    return _json({"ok": True})


@router.get("/summary")
async def get_surgery_summary(request: Request, _: bool = Depends(get_current_user)):
    cases = get_cases()
    summary = {
        "total": len(cases),
        "ready": 0,
        "warning": 0,
        "ongoing": 0,
        "cancelled": 0
    }
    for c in cases:
        stat = c.get("status")
        if stat == "준비완료":
            summary["ready"] += 1
        elif stat == "확인필요":
            summary["warning"] += 1
        elif stat == "진행중":
            summary["ongoing"] += 1
        elif stat == "취소":
            summary["cancelled"] += 1
            
    return _json(summary)


@router.get("/alerts")
async def get_surgery_alerts(request: Request, _: bool = Depends(get_current_user)):
    cases = get_cases()
    alerts = [c for c in cases if c.get("status") == "확인필요"]
    return _json({"alerts": alerts})


@router.get("/surgeons/summary")
async def get_surgeons_summary(request: Request, _: bool = Depends(get_current_user)):
    cases = get_cases()
    surgeon_data: Dict[str, Dict[str, int]] = {}
    
    for c in cases:
        surgeon = c.get("surgeon") or "Unknown"
        if surgeon not in surgeon_data:
            surgeon_data[surgeon] = {
                "total": 0,
                "ready": 0,
                "warning": 0,
                "ongoing": 0,
                "cancelled": 0
            }
            
        stats = surgeon_data[surgeon]
        stats["total"] += 1
        
        stat = c.get("status")
        if stat == "준비완료":
            stats["ready"] += 1
        elif stat == "확인필요":
            stats["warning"] += 1
        elif stat == "진행중":
            stats["ongoing"] += 1
        elif stat == "취소":
            stats["cancelled"] += 1
            
    # Convert to list
    result = []
    for s, stats in surgeon_data.items():
        result.append({
            "surgeon": s,
            **stats
        })
        
    # Sort by surgeon name
    result.sort(key=lambda x: x["surgeon"])
    return _json({"summary": result})


@router.post("/cases/{case_id}/cancel")
async def cancel_surgery_case(
    case_id: str, 
    payload: SurgeryCancelRequest, 
    _: bool = Depends(get_current_user)
):
    updated = cancel_case(case_id, payload.cancellation_reason)
    if not updated:
        raise HTTPException(status_code=404, detail="수술 일정을 찾을 수 없습니다.")
    return _json({"ok": True, "case": updated})


@router.post("/cases/{case_id}/restore")
async def restore_surgery_case(
    case_id: str, 
    _: bool = Depends(get_current_user)
):
    updated = restore_case(case_id)
    if not updated:
        raise HTTPException(status_code=404, detail="수술 일정을 찾을 수 없습니다.")
    return _json({"ok": True, "case": updated})


@router.get("/export.csv")
async def export_surgery_cases_csv(request: Request, _: bool = Depends(get_current_user)):
    cases = get_cases()
    
    # Sort: status == "확인필요" first, then surgery_date ascending
    def sort_key(c: Dict[str, Any]):
        is_warning = c.get("status") == "확인필요"
        date_val = c.get("surgery_date") or "9999-12-31"
        time_val = c.get("surgery_start_time") or "00:00"
        return (0 if is_warning else 1, date_val, time_val)
    cases.sort(key=sort_key)
    
    # CSV fields mapping to match requirements exactly
    headers = [
        "case_id", "patient_code", "surgery_date", "surgery_start_time", "surgery_end_time",
        "surgery_name", "surgeon", "operating_room", "anesthesia", "admission_type",
        "lab_date", "anesthesia_eval_done", "admission_confirmed", "consent_done",
        "preop_instruction_done", "fasting_instruction_done", "calendar_status",
        "is_cancelled", "status_auto", "missing_items", "notes", "created_at", "updated_at"
    ]
    
    output = io.StringIO()
    # Excel compatibility requires UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for c in cases:
        prep = c.get("prep") or {}
        missing_str = ", ".join(c.get("missing_items", []))
        row = [
            c.get("case_id", ""),
            c.get("patient_code", ""),
            c.get("surgery_date", ""),
            c.get("surgery_start_time", ""),
            c.get("surgery_end_time", ""),
            c.get("surgery_name", ""),
            c.get("surgeon", ""),
            c.get("operating_room", ""),
            c.get("anesthesia", ""),
            c.get("admission_type", ""),
            prep.get("lab_date", ""),
            "true" if prep.get("anesthesia_eval_done") else "false",
            "true" if prep.get("admission_confirmed") else "false",
            "true" if prep.get("consent_done") else "false",
            "true" if prep.get("preop_instruction_done") else "false",
            "true" if prep.get("fasting_instruction_done") else "false",
            c.get("calendar_status", "미연동"),
            "true" if c.get("is_cancelled") else "false",
            c.get("status_auto", ""),
            missing_str,
            c.get("notes", ""),
            c.get("created_at", ""),
            c.get("updated_at", "")
        ]
        writer.writerow(row)
        
    csv_data = output.getvalue()
    # Add UTF-8 BOM to prevent Excel encoding issues
    bom_csv_data = "\ufeff" + csv_data
    
    # Return as bytes streaming response
    byte_io = io.BytesIO(bom_csv_data.encode("utf-8"))
    
    from app.core_utils import get_now
    filename = f"surgery_schedules_{get_now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        byte_io,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/import.csv")
async def import_surgery_cases_csv(
    file: UploadFile = File(...), 
    _: bool = Depends(get_current_user)
):
    try:
        content = await file.read()
        decoded_content = content.decode("utf-8-sig", errors="ignore")
        
        f = io.StringIO(decoded_content)
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            raise HTTPException(status_code=400, detail="CSV 파일이 비어있습니다.")
            
        headers = [h.strip().strip('"').strip("'") for h in headers]
        
        header_map = {
            "case_id": "case_id", "수술ID": "case_id",
            "patient_code": "patient_code", "등록번호": "patient_code",
            "patient_name": "patient_name", "환자명": "patient_name",
            "surgery_date": "surgery_date", "수술일자": "surgery_date",
            "surgery_start_time": "surgery_start_time", "시작시간": "surgery_start_time",
            "surgery_end_time": "surgery_end_time", "종료시간": "surgery_end_time",
            "surgery_name": "surgery_name", "수술명": "surgery_name",
            "surgeon": "surgeon", "집도의": "surgeon",
            "operating_room": "operating_room", "수술실": "operating_room",
            "anesthesia": "anesthesia", "마취방법": "anesthesia",
            "admission_type": "admission_type", "입원구분": "admission_type",
            "lab_date": "lab_date", "검사일자": "lab_date", "검사일": "lab_date",
            "anesthesia_eval_done": "anesthesia_eval_done", "마취동의/평가": "anesthesia_eval_done", "마취 평가": "anesthesia_eval_done",
            "admission_confirmed": "admission_confirmed", "입원확인": "admission_confirmed", "입원 여부": "admission_confirmed",
            "consent_done": "consent_done", "수술동의서": "consent_done", "동의서": "consent_done",
            "preop_instruction_done": "preop_instruction_done", "수술전안내": "preop_instruction_done", "수술 전 설명": "preop_instruction_done",
            "fasting_instruction_done": "fasting_instruction_done", "금식안내": "fasting_instruction_done", "금식 안내": "fasting_instruction_done",
            "calendar_status": "calendar_status", "캘린더상태": "calendar_status", "캘린더 연동": "calendar_status",
            "notes": "notes", "비고": "notes"
        }
        
        mapped_headers = [header_map.get(h) for h in headers]
        
        # Verify required headers
        required = ["patient_code", "surgery_date", "surgery_name", "surgeon"]
        for req in required:
            if req not in mapped_headers:
                raise HTTPException(status_code=400, detail=f"필수 컬럼이 누락되었습니다: {req}")
                
        def parse_bool(val: str) -> bool:
            v = val.strip().lower()
            return v in ("완료", "y", "yes", "true", "1", "o")
            
        count = 0
        for row in reader:
            if not row or not any(row):
                continue
                
            case_data = {}
            prep_data = {}
            
            for idx, cell in enumerate(row):
                if idx >= len(mapped_headers):
                    break
                field = mapped_headers[idx]
                if not field:
                    continue
                    
                val = cell.strip()
                if not val:
                    continue
                
                # Check prep fields
                if field in ("lab_date", "anesthesia_eval_done", "admission_confirmed", "consent_done", "preop_instruction_done", "fasting_instruction_done"):
                    if field == "lab_date":
                        prep_data["lab_date"] = val
                    else:
                        prep_data[field] = parse_bool(val)
                elif field == "is_cancelled":
                    case_data["is_cancelled"] = parse_bool(val)
                else:
                    # Top-level fields
                    case_data[field] = val
                    
            if prep_data:
                case_data["prep"] = prep_data
                
            case_id = case_data.get("case_id")
            if case_id:
                existing = get_case(case_id)
                if existing:
                    # update existing
                    for k, v in case_data.items():
                        if k == "prep" and isinstance(v, dict):
                            if "prep" not in existing or not isinstance(existing["prep"], dict):
                                existing["prep"] = {}
                            existing["prep"].update(v)
                        else:
                            existing[k] = v
                    case_data = existing
                    
            save_case(case_data)
            count += 1
            
        # Write audit log for CSV import
        from app.surgery_store import write_audit_log
        write_audit_log(action="import_csv", case_id="csv_import", detail=f"Imported {count} cases via CSV")
        
        return _json({"ok": True, "count": count})
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to import CSV: {e}")
        return _error(f"CSV 가져오기 실패: {str(e)}", status_code=500)
