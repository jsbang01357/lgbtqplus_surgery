# Jisong Cloud

개인용 미니 클라우드 앱입니다.

현재 운영 기준은 `Starlette API + 정적 프론트엔드 + GCS + Gemini + Cloud Run` 조합입니다.  
앱 진입점은 [api_server.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/api_server.py)이며, [frontend/](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/frontend/)의 Apple 스타일 화면을 정적으로 제공하고 `/api/*` endpoint로 파일, 메모, AI, 도구 기능을 연결합니다.

## 현재 구조 한눈에 보기

- UI: `frontend/index.html`, `frontend/partials/*.html`, `frontend/styles.css`, `frontend/app.js`
- API: `api_server.py`
- 저장소: Google Cloud Storage
- AI: Gemini
- 배포: Docker, Cloud Build, Cloud Run
- 인증 경계: Cloudflare Access 선택 적용 + 앱 내부 패스키/계정 ID fallback

## 주요 기능

### 웹하드

- 파일 업로드
- 파일 목록 조회
- 개별 다운로드
- 개별 삭제
- ZIP 묶음 다운로드

업로드 파일은 GCS `uploads/` 아래에 저장되며, 같은 이름의 파일이 올라와도 타임스탬프를 붙여 덮어쓰지 않습니다.

### 메모장

- 메모 작성/수정
- 메모 목록 조회
- 개별 복사/다운로드/삭제
- ZIP 묶음 다운로드

메모는 GCS `memos/` 아래 `.txt` 파일로 저장되며, 제목과 생성/수정 시각을 본문 헤더와 blob metadata에 함께 반영합니다.

### AI

- Gemini 기반 파일 분석
- 메모 분석
- 직접 입력 텍스트 분석
- 프리셋 프롬프트
- 결과 복사, Markdown 다운로드, PDF 다운로드
- 결과를 새 메모로 저장
- 일/월 예상 비용 표시 및 사용 제한

PDF, 이미지, TXT, MD, CSV는 그대로 처리하고, DOCX/XLSX/PPTX는 앱에서 텍스트를 추출한 뒤 분석 프롬프트에 포함합니다. 예상 비용은 `logs/gemini_usage.json`을 기반으로 계산합니다.

### 도구모음

- 텍스트 클리너
- MD to PDF
- 글자 수 카운터
- 정산 계산기
- 저장소 상태
- 접속 기록 관리
- v6 파서 상태/연동 기반 기능

## 인증/권한 모델

현재 코드 기준 권한 경계는 아래와 같습니다.

- `웹하드`, `메모장`, `AI`: 인증 필요
- `도구모음`: 일부 열람 가능, 민감 기능은 인증 필요
- 접속 로그 조회/삭제, 비밀번호 변경, 폴더 동기화, v6 parse 같은 민감 API: 인증 필요

인증 방식:

1. Cloudflare Access
2. 패스키 세션
3. 소유자 계정 ID + 비밀번호 fallback
4. 일부 환경에서 Google Access fallback

실제 상태 확인 endpoint는 `/api/session`입니다.

## 저장 구조

```text
bucket/
├── uploads/
├── memos/
├── logs/
│   ├── access_log.json
│   └── gemini_usage.json
└── auth/
    ├── account_password.txt
    ├── account_sessions.json
    └── passkeys.json
```

## 프로젝트 구조

```text
.
├── api_server.py
├── app/
│   ├── access_logger.py
│   ├── ai.py
│   ├── auth.py
│   ├── config.py
│   ├── core_utils.py
│   ├── folder_sync.py
│   ├── gcs_helper.py
│   ├── idle_timeout.py
│   ├── md_pdf.py
│   ├── memo.py
│   ├── passkeys.py
│   ├── request_utils.py
│   ├── security.py
│   ├── settlement.py
│   ├── storage.py
│   ├── streamlit_compat.py
│   ├── text_cleaner.py
│   ├── tools.py
│   └── v6_bridge.py
├── docs/
├── frontend/
├── tests/
├── v6/
├── Dockerfile
├── cloudbuild.yaml
└── requirements.txt
```

### 주요 파일 역할

- [api_server.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/api_server.py): API 라우팅, 인증 확인, 정적 프론트엔드 제공
- [app/storage.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/storage.py): 파일 저장/목록/다운로드/ZIP
- [app/memo.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/memo.py): 메모 CRUD
- [app/ai.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/ai.py): Gemini 분석, 비용 계산, 결과 후처리
- [app/security.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/security.py): 계정 비밀번호 해시/검증, Access 정책 보조
- [app/passkeys.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/passkeys.py): WebAuthn 패스키 등록/로그인
- [app/folder_sync.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/folder_sync.py): 폴더 스캔/동기화
- [app/v6_bridge.py](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/v6_bridge.py): Python API와 Node parser-core 연결
- [frontend/README.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/frontend/README.md): 프론트엔드 구조 메모

## 주요 API

- `GET /api/health`
- `GET /api/session`
- `POST /api/auth/account/login`
- `POST /api/auth/passkey/register/options`
- `POST /api/auth/passkey/register/verify`
- `POST /api/auth/passkey/login/options`
- `POST /api/auth/passkey/login/verify`
- `POST /api/auth/logout`
- `GET /api/files`
- `POST /api/files`
- `GET /api/files/download`
- `POST /api/files/delete`
- `GET /api/files/zip`
- `GET /api/memos`
- `POST /api/memos`
- `GET /api/memos/{file_name}`
- `GET /api/memos/{file_name}/download`
- `POST /api/memos/delete`
- `GET /api/memos/zip`
- `POST /api/ai/analyze`
- `POST /api/tools/markdown-pdf`
- `POST /api/tools/text-cleaner`
- `POST /api/tools/settlement`
- `GET /api/usage/summary`
- `GET /api/sync/status`
- `POST /api/sync/rescan`
- `GET /api/v6/health`
- `POST /api/v6/parse`
- `POST /api/v6/publish`

## 실행 방법

### 1. 의존성 설치

```bash
python3 -m pip install -r requirements.txt
```

macOS에서 MD to PDF를 로컬로 쓰려면 WeasyPrint 시스템 라이브러리도 필요합니다.

```bash
brew install glib pango gdk-pixbuf libffi
```

### 2. 로컬 설정

설정은 환경변수 또는 `.streamlit/secrets.toml`에서 읽습니다.

예시:

```toml
[gcs]
bucket_name = "YOUR_BUCKET_NAME"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"

[gemini]
api_key = "YOUR_GEMINI_API_KEY"
model = "gemini-3-flash-preview"
input_price_per_1m = 0.50
output_price_per_1m = 3.00
usd_to_krw_rate = 1478

[admin]
admin_password = "YOUR_ADMIN_PASSWORD"
```

중요 환경변수:

- `GCS_BUCKET_NAME`
- `GCP_SERVICE_ACCOUNT_JSON`
- `GEMINI_API_KEY`
- `ADMIN_PASSWORD`
- `REQUIRE_CLOUDFLARE_ACCESS`
- `ALLOW_ACCOUNT_ID_FALLBACK`
- `JISONG_ACCOUNT_LOGIN_ID`
- `PASSKEY_RP_ID`
- `PASSKEY_ORIGIN`
- `PASSKEY_RP_NAME`

### 3. 로컬 실행

```bash
uvicorn api_server:app --host 127.0.0.1 --port 8080
```

브라우저에서 `http://127.0.0.1:8080`을 엽니다.

## 검증 방법

기본 파이썬 검증:

```bash
python3 -m unittest discover -s tests/python
```

v6 parser-core 타입 체크:

```bash
cd v6/parser-core
npm run check
```

주의:

- 현재 로컬 머신의 Node가 `v16`이면 `v6/parser-core` 작업 전에 Node 20 계열로 맞추는 편이 안전합니다.
- `tests/python`은 `google-cloud-storage`, `cryptography` 같은 런타임 의존성이 설치되어 있어야 수집 단계부터 정상 동작합니다.

## 배포

[cloudbuild.yaml](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/cloudbuild.yaml) 기준 배포 흐름:

1. Docker 이미지 빌드
2. Artifact Registry 푸시
3. Cloud Run 서비스 업데이트

현재 Cloud Run 설정 핵심값:

- 서비스: `jisong-cloud-tokyo`
- 리전: `asia-northeast1`
- 버킷: `jisong-cloud-storage`
- Gemini API key: Secret Manager `gemini-api-key`
- Access 강제 여부: `REQUIRE_CLOUDFLARE_ACCESS`
- 계정 ID fallback 허용 여부: `ALLOW_ACCOUNT_ID_FALLBACK`

## 관련 문서

- [DESIGN.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/DESIGN.md)
- [docs/gcp-security-plan.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/docs/gcp-security-plan.md)
- [docs/v6-parser-core-plan.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/docs/v6-parser-core-plan.md)
- [docs/mac-folder-sync-csv-plan.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/docs/mac-folder-sync-csv-plan.md)
- [frontend/README.md](/Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/frontend/README.md)
