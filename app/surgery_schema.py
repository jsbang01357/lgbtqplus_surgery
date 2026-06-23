from pydantic import BaseModel
from typing import Optional, List

class PremedDetailSchema(BaseModel):
    writer: Optional[str] = ""
    lab_checker: Optional[str] = ""
    coop_checker: Optional[str] = ""
    amount: Optional[str] = ""
    consent_admission: Optional[bool] = False
    consent_surgery: Optional[bool] = False
    consent_discharge: Optional[bool] = False
    premed_notes: Optional[str] = ""
    
    # 과거력 및 복용약
    history_disease: Optional[str] = ""
    history_disease_year: Optional[str] = ""
    history_med_name: Optional[str] = ""
    history_med_dose: Optional[str] = ""
    history_med_frequency: Optional[str] = ""
    history_med_stop_date: Optional[str] = ""
    history_hormone_med: Optional[str] = ""
    history_hormone_dose: Optional[str] = ""
    history_hormone_period: Optional[str] = ""
    history_surgery_history: Optional[str] = ""
    history_surgery_year: Optional[str] = ""
    history_surgery_hospital: Optional[str] = ""
    history_allergy: Optional[str] = ""
    
    # 수술 전 검사 확인
    exam_ekg: Optional[str] = ""
    exam_chest: Optional[str] = ""
    exam_lab_notes: Optional[str] = ""

class SurgeryPrepSchema(BaseModel):
    lab_date: Optional[str] = ""
    lab_scheduled_date: Optional[str] = ""
    lab_completed_date: Optional[str] = ""
    lab_status: Optional[str] = ""
    
    # Legacy fields (maintained for backward compatibility)
    anesthesia_eval_done: Optional[bool] = False
    admission_confirmed: Optional[bool] = False
    consent_done: Optional[bool] = False
    preop_instruction_done: Optional[bool] = False
    fasting_instruction_done: Optional[bool] = False
    
    # Extended fields
    premed_status: Optional[str] = "미완료"
    cooperation_status: Optional[str] = "불필요"
    admission_guidance_done: Optional[bool] = False
    documents_checked: Optional[bool] = False
    last_checker: Optional[str] = ""
    last_checked_date: Optional[str] = ""
    prep_memo: Optional[str] = ""
    
    # Premed details
    premed_detail: PremedDetailSchema = PremedDetailSchema()

class SurgeryCaseCreate(BaseModel):
    patient_code: str
    patient_name: Optional[str] = ""
    patient_preferred_name: Optional[str] = ""
    surgery_date: str
    surgery_start_time: str
    surgery_end_time: str
    surgery_name: str
    surgeon: str
    operating_room: str
    anesthesia: str
    admission_type: str
    
    # Extended basic info
    diagnosis: Optional[str] = ""
    coop_detail: Optional[str] = ""
    insurance_types: Optional[List[str]] = []
    surgery_fee: Optional[str] = ""
    surgery_duration: Optional[int] = 0
    room_type: Optional[str] = ""
    
    # Calendar fields
    calendar_status: Optional[str] = "미연동"
    calendar_event_id: Optional[str] = ""
    
    notes: Optional[str] = ""
    
    # Nested prep checklist
    prep: SurgeryPrepSchema = SurgeryPrepSchema()
    
    # 가예약 / Pending
    surgery_status: Optional[str] = "예정"
    pending_requester: Optional[str] = ""
    pending_registered_date: Optional[str] = ""
    pending_deadline: Optional[str] = ""
    is_confirmed: Optional[bool] = False
    pending_memo: Optional[str] = ""
    
    # 2주 전 확인 전화
    an_call_required: Optional[bool] = False
    an_call_scheduled_date: Optional[str] = ""
    an_call_completed_date: Optional[str] = ""
    an_call_checker: Optional[str] = ""
    an_call_patient_intent: Optional[str] = "미정"
    an_call_notes: Optional[str] = ""
    an_call_followup_needed: Optional[bool] = False
    
    # 1인실 예약
    room_1person_required: Optional[bool] = False
    room_1person_status: Optional[str] = "미정"
    room_memo: Optional[str] = ""
    
    # 성중립병실 확인
    room_gender_neutral_required: Optional[bool] = False
    room_gender_neutral_consent: Optional[bool] = False
    room_gender_neutral_status: Optional[str] = "불필요"
    room_gender_neutral_checker: Optional[str] = ""
    room_gender_neutral_checked_date: Optional[str] = ""
    
    # Co-op 수술
    coop_status: Optional[str] = "불필요"
    coop_dept: Optional[str] = ""
    coop_doctor: Optional[str] = ""
    coop_notes: Optional[str] = ""
    coop_confirmed: Optional[bool] = False
    coop_memo: Optional[str] = ""

class SurgeryCaseUpdate(BaseModel):
    patient_code: Optional[str] = None
    patient_name: Optional[str] = None
    patient_preferred_name: Optional[str] = None
    surgery_date: Optional[str] = None
    surgery_start_time: Optional[str] = None
    surgery_end_time: Optional[str] = None
    surgery_name: Optional[str] = None
    surgeon: Optional[str] = None
    operating_room: Optional[str] = None
    anesthesia: Optional[str] = None
    admission_type: Optional[str] = None
    
    diagnosis: Optional[str] = None
    coop_detail: Optional[str] = None
    insurance_types: Optional[List[str]] = None
    surgery_fee: Optional[str] = None
    surgery_duration: Optional[int] = None
    room_type: Optional[str] = None
    
    calendar_status: Optional[str] = None
    calendar_event_id: Optional[str] = None
    
    notes: Optional[str] = None
    prep: Optional[SurgeryPrepSchema] = None
    
    surgery_status: Optional[str] = None
    pending_requester: Optional[str] = None
    pending_registered_date: Optional[str] = None
    pending_deadline: Optional[str] = None
    is_confirmed: Optional[bool] = None
    pending_memo: Optional[str] = None
    
    an_call_required: Optional[bool] = None
    an_call_scheduled_date: Optional[str] = None
    an_call_completed_date: Optional[str] = None
    an_call_checker: Optional[str] = None
    an_call_patient_intent: Optional[str] = None
    an_call_notes: Optional[str] = None
    an_call_followup_needed: Optional[bool] = None
    
    room_1person_required: Optional[bool] = None
    room_1person_status: Optional[str] = None
    room_memo: Optional[str] = None
    
    room_gender_neutral_required: Optional[bool] = None
    room_gender_neutral_consent: Optional[bool] = None
    room_gender_neutral_status: Optional[str] = None
    room_gender_neutral_checker: Optional[str] = None
    room_gender_neutral_checked_date: Optional[str] = None
    
    coop_status: Optional[str] = None
    coop_dept: Optional[str] = None
    coop_doctor: Optional[str] = None
    coop_notes: Optional[str] = None
    coop_confirmed: Optional[bool] = None
    coop_memo: Optional[str] = None

class SurgeryCancelRequest(BaseModel):
    cancellation_reason: str
