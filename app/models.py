from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AccountLoginRequest(BaseModel):
    account_id: str
    password: str

class PasswordUpdateRequest(BaseModel):
    new_password: str

class PasskeyRegisterVerifyRequest(BaseModel):
    id: str
    rawId: str
    type: str
    response: Dict[str, Any]

class PasskeyLoginVerifyRequest(BaseModel):
    id: str
    rawId: str
    type: str
    response: Dict[str, Any]

class FileDeleteRequest(BaseModel):
    blob_name: str

class FileSaveContentRequest(BaseModel):
    blob_name: str
    content: str

class MemoSaveRequest(BaseModel):
    title: str
    content: str
    file_name: Optional[str] = None

class MemoDeleteRequest(BaseModel):
    file_name: str

class TextCleanerRequest(BaseModel):
    text: str
    mode: str = "basic"
    options: Dict[str, Any] = {}

class SettlementRequest(BaseModel):
    people: List[str]
    expenses: List[Dict[str, Any]]

class V6ParseRequest(BaseModel):
    raw_text: Optional[str] = None
    text: Optional[str] = None
    patient_id: Optional[str] = "patient_001"
    source: Optional[str] = "emr"
    source_path: Optional[str] = ""

class V6PublishRequest(BaseModel):
    documents: List[Dict[str, Any]]
    manifest: Optional[List[Dict[str, Any]]] = None

class AIAnalyzeRequest(BaseModel):
    prompt: str
    blob_names: Optional[List[str]] = []
    memo_file_names: Optional[List[str]] = []
    extra_text: Optional[str] = ""

class MarkdownPdfRequest(BaseModel):
    markdown: str
