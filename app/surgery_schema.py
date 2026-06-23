from pydantic import BaseModel
from typing import Optional

class SurgeryPrepSchema(BaseModel):
    lab_date: Optional[str] = ""
    anesthesia_eval_done: Optional[bool] = False
    admission_confirmed: Optional[bool] = False
    consent_done: Optional[bool] = False
    preop_instruction_done: Optional[bool] = False
    fasting_instruction_done: Optional[bool] = False

class SurgeryCaseCreate(BaseModel):
    patient_code: str
    patient_name: Optional[str] = ""
    surgery_date: str
    surgery_start_time: str
    surgery_end_time: str
    surgery_name: str
    surgeon: str
    operating_room: str
    anesthesia: str
    admission_type: str
    
    # Calendar fields
    calendar_status: Optional[str] = "미연동"
    calendar_event_id: Optional[str] = ""
    
    notes: Optional[str] = ""
    
    # Nested prep checklist
    prep: SurgeryPrepSchema = SurgeryPrepSchema()

class SurgeryCaseUpdate(BaseModel):
    patient_code: Optional[str] = None
    patient_name: Optional[str] = None
    surgery_date: Optional[str] = None
    surgery_start_time: Optional[str] = None
    surgery_end_time: Optional[str] = None
    surgery_name: Optional[str] = None
    surgeon: Optional[str] = None
    operating_room: Optional[str] = None
    anesthesia: Optional[str] = None
    admission_type: Optional[str] = None
    
    # Calendar fields
    calendar_status: Optional[str] = None
    calendar_event_id: Optional[str] = None
    
    notes: Optional[str] = None
    
    # Nested prep checklist
    prep: Optional[SurgeryPrepSchema] = None

class SurgeryCancelRequest(BaseModel):
    cancellation_reason: str
