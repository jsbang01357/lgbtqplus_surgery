# Qplus Surgery Workspace Context

Qplus Surgery는 수술 일정 운영을 위한 내부망 대시보드입니다. 현재 우선순위는 오프라인 안정 운영이며, 클라우드 기능은 선택 경로입니다.

## 현재 운영 기준

```text
Browser
└── FastAPI api_server.py
    ├── Static frontend
    ├── Auth/session/passkey
    ├── Surgery API
    └── Storage backend
        ├── local file storage 기본
        └── GCS 선택
```

## 핵심 파일

- `api_server.py`: FastAPI 앱 생성, 라우터 연결, 정적 프론트엔드 제공
- `app/routers/auth.py`: 계정 로그인, 공개 회원가입 차단, passkey, Google OAuth 선택 경로
- `app/routers/surgery.py`: 수술 케이스 CRUD, 요약, 알림, CSV import/export, Calendar 상태 API
- `app/surgery_store.py`: 케이스 저장/조회/삭제, audit log, Calendar 동기화 호출
- `app/surgery_status.py`: 준비 상태 자동 계산
- `app/surgery_schema.py`: 수술 케이스 Pydantic schema
- `app/gcs_helper.py`: GCS와 로컬 파일 저장소를 같은 bucket/blob 인터페이스로 제공
- `app/config.py`: 환경변수, `.env`, `.streamlit/secrets.toml` 설정 로딩
- `frontend/app.js`: SPA 상태 관리, API 호출, 모달/테이블 렌더링
- `frontend/partials/surgery.html`: 수술 대시보드 화면

## 저장소 백엔드

기본:

```env
STORAGE_BACKEND="local"
OFFLINE_MODE="true"
LOCAL_STORAGE_ROOT=".local_data/storage"
```

로컬 백엔드는 GCS 객체 경로를 파일 경로로 그대로 매핑합니다.

```text
surgery_ops/cases/case_1.json
-> .local_data/storage/surgery_ops/cases/case_1.json
```

GCS 전환:

```env
STORAGE_BACKEND="gcs"
OFFLINE_MODE="false"
GCS_BUCKET_NAME="lgbtqplus-surgery"
```

## 인증 모델

권장 오프라인 운영:

- Cloudflare Access 비활성화
- 계정 ID/password fallback 활성화
- 공개 회원가입 비활성화
- passkey는 내부망 주소 기준으로 선택 사용

관련 설정:

```env
REQUIRE_CLOUDFLARE_ACCESS="false"
ALLOW_ACCOUNT_ID_FALLBACK="true"
ALLOW_PUBLIC_REGISTRATION="false"
PASSKEY_RP_ID="맥미니IP"
PASSKEY_ORIGIN="http://맥미니IP:8080"
```

역할:

- `admin`: 전체 관리
- `staff`: 케이스 생성/수정/삭제
- `viewer`: 조회 중심

## 상태 계산

`compute_case_status()`가 다음 값을 계산합니다.

- `status`
- `status_auto`
- `missing_items`
- `days_until_surgery`
- `is_lab_valid`

주요 기준:

- 취소 케이스는 `취소`
- 오늘 수술은 `진행중`
- 검사일 누락 또는 8주 초과는 즉시 `확인필요`
- 수술 14일 이내 프리메드/협진/입원안내/서류확인 미완료는 `확인필요`
- 그 외는 `준비완료`

## Calendar 정책

오프라인 기본:

```env
GOOGLE_CALENDAR_SYNC_ENABLED="false"
```

이 경우:

- Calendar service를 만들지 않습니다.
- 저장 시 네트워크 호출이 없습니다.
- 프론트엔드에는 오프라인 상태가 표시됩니다.

Calendar를 켜더라도 외부 캘린더에는 환자명, 선호이름, 진단명, 상세 비고 같은 민감 정보를 넣지 않는 정책을 유지합니다.

## 검증 명령

```bash
.venv/bin/python -m unittest tests/python/test_config.py tests/python/test_gcs.py tests/python/test_surgery_status.py
node --check frontend/app.js
.venv/bin/python -m py_compile api_server.py app/*.py app/routers/*.py
```

## 현재 주의점

- parser-core는 현재 수술 대시보드 필수 경로가 아닙니다.
- 전체 테스트는 외부 서비스 초기화 때문에 느릴 수 있어 빠른 검증 세트를 우선 사용합니다.
- `.local_data/`와 `.env`는 git에 올리지 않습니다.
- 운영 데이터 백업 기준은 `.local_data/storage/`입니다.
