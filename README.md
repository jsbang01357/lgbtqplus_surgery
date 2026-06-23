# Qplus Surgery

Qplus Surgery는 병원 내부망에서 수술 일정을 등록, 확인, 수정, 취소하고 준비 상태를 추적하는 오프라인 우선 대시보드입니다.

현재 기본 운영 기준은 `FastAPI + 정적 프론트엔드 + 로컬 파일 저장소`입니다. GCS와 Google Calendar 연동은 선택 기능이며, 오프라인 모드에서는 네트워크 호출 없이 로컬 디스크에 데이터를 저장합니다.

## 빠른 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8080
```

접속 주소:

- 맥미니 본인: `http://127.0.0.1:8080`
- 내부망 PC: `http://맥미니IP:8080`

## 오프라인 기본 설정

`.env.example`의 기본값은 오프라인 운영에 맞춰져 있습니다.

```env
STORAGE_BACKEND="local"
OFFLINE_MODE="true"
LOCAL_STORAGE_ROOT=".local_data/storage"
GOOGLE_CALENDAR_SYNC_ENABLED="false"
REQUIRE_CLOUDFLARE_ACCESS="false"
ALLOW_ACCOUNT_ID_FALLBACK="true"
ALLOW_PUBLIC_REGISTRATION="false"
```

운영 전 반드시 바꿀 값:

- `JISONG_ACCOUNT_LOGIN_ID`
- `ADMIN_PASSWORD`
- `PASSKEY_RP_ID`
- `PASSKEY_ORIGIN`

내부망에서 접속할 경우 `PASSKEY_RP_ID`와 `PASSKEY_ORIGIN`은 맥미니 IP 기준으로 맞춥니다.

```env
PASSKEY_RP_ID="192.168.0.35"
PASSKEY_ORIGIN="http://192.168.0.35:8080"
```

## 데이터 저장 위치

오프라인 모드에서는 GCS 객체 경로를 그대로 로컬 파일 경로로 저장합니다.

```text
.local_data/storage/
├── surgery_ops/
│   ├── cases/
│   │   └── case_*.json
│   └── audit/
│       └── surgery_ops_audit.jsonl
├── auth/
│   ├── account_password.txt
│   ├── account_sessions.json
│   ├── passkeys.json
│   └── users.json
└── logs/
    └── access_log.json
```

백업은 `.local_data/storage/` 폴더를 통째로 복사하면 됩니다.

## 주요 기능

- 수술 일정 등록, 조회, 수정, 삭제
- 수술 취소 및 복구
- CSV 가져오기와 내보내기
- 상태 자동 계산
- 집도의별 요약
- 확인 필요 항목 알림
- 계정 로그인, 역할 기반 권한, passkey 세션
- 선택적 Google Calendar 동기화

## 상태 계산 기준

수술 케이스는 저장/조회 시 자동으로 상태가 계산됩니다.

- `취소`: 취소 처리된 케이스
- `진행중`: 수술일이 오늘인 케이스
- `확인필요`: 검사일 누락, 검사일 8주 초과, 캘린더 오류, 14일 이내 필수 준비 미완료
- `준비완료`: 위 위험 조건이 없는 케이스

필수 준비 항목:

- 검사일
- 프리메드 상태
- 협진 상태
- 입원 안내
- 서류 확인

## API 구조

진입점:

- `api_server.py`

주요 라우터:

- `app/routers/auth.py`
- `app/routers/surgery.py`

주요 엔드포인트:

- `GET /api/health`
- `GET /api/session`
- `POST /api/auth/account/login`
- `POST /api/auth/account/register`
- `POST /api/auth/logout`
- `GET /api/surgery/cases`
- `POST /api/surgery/cases`
- `GET /api/surgery/cases/{case_id}`
- `PUT /api/surgery/cases/{case_id}`
- `DELETE /api/surgery/cases/{case_id}`
- `POST /api/surgery/cases/{case_id}/cancel`
- `POST /api/surgery/cases/{case_id}/restore`
- `GET /api/surgery/summary`
- `GET /api/surgery/alerts`
- `GET /api/surgery/surgeons/summary`
- `GET /api/surgery/export.csv`
- `POST /api/surgery/import.csv`
- `GET /api/surgery/calendar/status`
- `POST /api/surgery/calendar/disconnect`

## 프로젝트 구조

```text
.
├── api_server.py
├── app/
│   ├── api_deps.py
│   ├── calendar_helper.py
│   ├── config.py
│   ├── gcs_helper.py
│   ├── passkeys.py
│   ├── security.py
│   ├── surgery_schema.py
│   ├── surgery_status.py
│   ├── surgery_store.py
│   └── routers/
│       ├── auth.py
│       └── surgery.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── partials/
├── docs/
├── tests/
├── scripts/
├── Dockerfile
└── requirements.txt
```

## 검증

빠른 핵심 검증:

```bash
.venv/bin/python -m unittest tests/python/test_config.py tests/python/test_gcs.py tests/python/test_surgery_status.py
node --check frontend/app.js
.venv/bin/python -m py_compile api_server.py app/*.py app/routers/*.py
```

전체 Python 테스트:

```bash
.venv/bin/python -m unittest discover -s tests/python
```

parser-core TypeScript 검증은 의존성 설치 후 실행합니다.

```bash
npm --prefix parser-core ci
npm --prefix parser-core run check
```

## 선택: GCS/Cloud Run 운영

클라우드 저장소를 쓰려면 `.env` 또는 Cloud Run 환경변수에서 아래처럼 설정합니다.

```env
STORAGE_BACKEND="gcs"
OFFLINE_MODE="false"
GCS_BUCKET_NAME="lgbtqplus-surgery"
GCP_SERVICE_ACCOUNT_JSON="..."
```

Google Calendar를 켜려면:

```env
GOOGLE_CALENDAR_SYNC_ENABLED="true"
GOOGLE_CALENDAR_ID="primary"
GDRIVE_CLIENT_ID="..."
GDRIVE_CLIENT_SECRET="..."
GDRIVE_REDIRECT_URI="http://맥미니IP:8080/api/auth/gdrive/callback"
```

오프라인 운영에서는 Calendar 동기화를 켜지 않는 것을 권장합니다.

## 운영 원칙

- 실제 환자 이름은 가능하면 앱 내부 저장에만 두고 외부 캘린더에는 넣지 않습니다.
- 공개 회원가입은 기본 비활성화합니다.
- `.env`, `.local_data/`, `.streamlit/`은 git에 올리지 않습니다.
- 백업은 `.local_data/storage/` 기준으로 주기적으로 보관합니다.
- 기능 추가 전에는 `tasks/todo.md`, 반복 실수는 `tasks/lessons.md`에 기록합니다.
