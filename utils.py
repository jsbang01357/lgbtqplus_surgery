import datetime
import re

KST = datetime.timezone(datetime.timedelta(hours=9))

def get_now():
    """현재 시간을 KST 기준으로 반환합니다."""
    return datetime.datetime.now(KST)

def safe_filename(title: str) -> str:
    """공백을 밑줄로 바꾸고 특수문자를 제거하여 안전한 파일명을 만듭니다."""
    s = str(title).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)
