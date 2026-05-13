# Jisong Cloud

개인용 Streamlit 기반 미니 클라우드 앱입니다.

파일 보관, 메모 관리, 텍스트 정리, 간단한 유틸리티를 한곳에 모아 둔 실사용 중심 프로젝트입니다.  
UI보다 빠른 사용성과 단순한 운영을 우선하며, 데이터 저장소는 Google Cloud Storage(GCS)를 사용합니다.

현재 코드 기준 버전 표기는 앱 푸터에 표시되는 `Ver 3.0 (260429)`를 따릅니다.

---

## 프로젝트 개요

이 프로젝트는 하나의 Streamlit 앱에서 아래 네 가지 영역을 제공합니다.

1. 웹하드
2. 메모장
3. AI
4. 도구모음

메인 진입점은 `jisong_cloud.py`이며, 사이드바 메뉴를 기준으로 각 기능 화면을 라우팅합니다.

---

## 주요 기능

### 1. 웹하드
- 파일 업로드
- 저장된 파일 목록 조회
- 개별 다운로드
- 개별 삭제
- 전체 ZIP 생성 후 다운로드
- 전체 삭제

업로드된 파일은 GCS의 `uploads/` prefix 아래에 저장됩니다.

파일명은 업로드 시각이 붙은 형태로 저장되어, 같은 이름의 파일이 올라와도 덮어쓰지 않도록 구성되어 있습니다.

### 2. 메모장
- 새 메모 작성
- 저장된 메모 목록 조회
- 메모 내용 수정
- 개별 복사
- 개별 다운로드
- 개별 삭제
- 전체 ZIP 생성 후 다운로드
- 전체 삭제

메모는 GCS의 `memos/` prefix 아래 `.txt` 파일로 저장됩니다.  
메모 제목, 생성 시간, 수정 시간은 파일 본문 헤더와 blob metadata 양쪽에 반영됩니다.

### 3. AI
- Gemini 기반 파일 분석
- 메모장 텍스트 분석
- 직접 입력 텍스트 분석
- SOAP 발표, 예상 Q&A 등 자주 쓰는 요청 프리셋
- 사용자 질문 기반 요약/정리
- 오늘/이번 달 예상 Gemini 비용을 원화로 표시
- 분석 결과 복사, Markdown 다운로드, PDF 다운로드
- 분석 결과를 새 메모로 저장

AI 메뉴는 Gemini 3 Flash Preview를 사용하며, GCS의 `uploads/` 파일 중 PDF, 이미지, DOCX, XLSX, PPTX, TXT, MD, CSV 파일과 `memos/`의 텍스트 메모를 선택해 분석합니다.  
질문 입력칸에는 임상 발표와 교수님 질의응답 준비용 프리셋 버튼으로 반복 요청을 빠르게 추가할 수 있습니다.  
예상 비용은 Gemini 응답의 token usage를 `logs/gemini_usage.json`에 저장한 뒤, Gemini 3 Flash Preview 유료 Standard 단가와 앱 내 USD/KRW 환산값 기준으로 원화 계산합니다.  
개인 파일과 메모 저장 기능을 다루므로 웹하드/메모장과 동일하게 인증 후 접근합니다.
DOCX, XLSX, PPTX는 Gemini에 원본 파일을 직접 업로드하지 않고, 앱에서 텍스트를 추출해 분석 프롬프트에 포함합니다.

### 4. 도구모음
현재 포함된 도구는 아래와 같습니다.

- 텍스트 클리너
- MD to PDF
- 글자수 카운터
- 정산 계산기
- 오늘 뭐 먹지?
- 접속 기록 관리

#### 텍스트 클리너
- AI 답변/복붙 텍스트 정리용 기본 모드
- 불릿 기호 정리
- 구분선 제거
- 줄바꿈/공백 정리
- URL 제거, 특수문자 제거, 번호 제거 등 상세 옵션 제공

#### 글자수 카운터
- 단어 수
- 공백 포함 글자 수
- 공백 제외 글자 수
- 예상 A4 분량

#### MD to PDF
- Markdown 텍스트 직접 입력
- `.md`, `.markdown`, `.txt` 파일 업로드
- 표, 코드블록, 한글 폰트를 포함한 PDF 다운로드

#### 정산 계산기
- 사람 목록 입력
- 지출별 돈낸사람, 비용, n빵할사람, 항목 입력
- n빵할사람을 비우면 전체 n빵으로 계산
- 균등 분할 기준 사람별 잔액 계산
- 최소 송금 목록을 문장형으로 표시

#### 오늘 뭐 먹지?
- `data/menu_list.json`에 있는 메뉴 중 하나를 랜덤 추천

#### 접속 기록 관리
- 최근 최대 500건의 접속 기록 조회
- 접속 시간, IP 주소, 브라우저 정보 표시
- 관리자 비밀번호 재입력 후 전체 로그 삭제 가능

---

## 인증 정책

현재 구현 기준으로 인증은 관리자 비밀번호 하나를 기준으로 동작합니다.

- `웹하드` 접근 시 인증 필요
- `메모장` 접근 시 인증 필요
- `AI` 접근 시 인증 필요
- `도구모음` 자체는 열람 가능
- 단, `접속 기록 관리`는 도구모음 내부에서도 인증 필요

인증 상태는 Streamlit `session_state`에 저장되는 단순 세션 기반 방식입니다.

---

## 저장 구조

하나의 GCS 버킷 안에서 prefix를 나눠 데이터를 관리합니다.

```text
bucket/
├── uploads/
│   └── ...
├── memos/
│   └── *.txt
└── logs/
    ├── access_log.json
    └── gemini_usage.json
```

### 파일 저장
- 업로드 파일은 `uploads/파일명_타임스탬프.확장자` 형태로 저장됩니다.

### 메모 저장
- 메모는 텍스트 파일 하나당 메모 하나 구조입니다.
- 파일 본문은 아래와 같은 헤더를 포함합니다.

```text
TITLE: 메모 제목
CREATED_AT: 2026-04-24 12:34:56
UPDATED_AT: 2026-04-24 12:34:56

메모 본문...
```

### 접속 로그 저장
- 접속 로그는 `logs/access_log.json`에 JSON 배열 형태로 저장됩니다.
- 새 기록이 앞에 추가되며, 최대 500건까지만 유지합니다.

### Gemini 사용량 로그 저장
- Gemini 사용량은 `logs/gemini_usage.json`에 JSON 배열 형태로 저장됩니다.
- 환자 자료나 프롬프트 본문은 저장하지 않고, 시간, 모델명, 토큰 수, 예상 비용만 기록합니다.

---

## 현재 구현 기준 동작 메모

README를 코드 기준으로 맞춘 현재 시점에서, 아래 사항은 실제 동작을 이해할 때 중요합니다.

- 파일 다운로드는 현재 Signed URL 직접 다운로드 방식이 아니라, Streamlit `download_button`에 데이터를 실어 내려주는 방식입니다.
- ZIP 파일은 사용자가 버튼을 눌렀을 때만 메모리에서 생성됩니다.
- 파일 목록과 메모 목록, 일부 다운로드/ZIP 생성은 Streamlit 캐시를 사용합니다.
- 파일 개별 다운로드와 AI 결과 PDF는 사용자가 준비 버튼을 눌렀을 때만 데이터를 생성합니다.
- 접속 로그는 앱 진입 시 세션당 한 번 기록되도록 되어 있습니다.
- 10분 동안 입력이 없으면 브라우저 창 닫기를 시도하며, 브라우저 정책상 실패할 경우 안내 화면을 표시합니다.
- Gemini 분석 결과는 별도 파일로 저장하지 않고, 버튼을 눌렀을 때 새 메모로 저장합니다.
- Gemini 예상 비용 로그는 최근 1,000건까지만 유지하며, GCS 조건부 업로드로 동시 쓰기 충돌을 줄입니다.

---

## 프로젝트 구조

```text
.
├── jisong_cloud.py
├── app/
│   ├── __init__.py
│   ├── access_logger.py
│   ├── ai.py
│   ├── auth.py
│   ├── core_utils.py
│   ├── gcs_helper.py
│   ├── idle_timeout.py
│   ├── md_pdf.py
│   ├── memo.py
│   ├── settlement.py
│   ├── storage.py
│   ├── streamlit_compat.py
│   ├── text_cleaner.py
│   └── tools.py
├── components/
│   ├── __init__.py
│   └── custom_copy_btn/
│       ├── __init__.py
│       └── frontend/
│           ├── index.html
│           └── streamlit-component-lib.js
├── data/
│   └── menu_list.json
├── tasks/
│   └── todo.md
├── tests/
│   └── test_settlement.py
├── AGENTS.md
├── cloudbuild.yaml
├── Dockerfile
├── jisong_cloud.code-workspace
└── requirements.txt
```

### 파일별 역할

- `jisong_cloud.py`: 앱 진입점, 사이드바 메뉴, 인증 분기, 화면 라우팅
- `app/ai.py`: Gemini 기반 파일/텍스트 분석 및 메모 저장
- `app/gcs_helper.py`: GCS 클라이언트 생성 및 버킷 이름 확인
- `app/storage.py`: 웹하드 업로드/목록/다운로드/삭제/ZIP 처리
- `app/memo.py`: 메모 CRUD 및 메모 ZIP 처리
- `app/tools.py`: 도구모음 화면 구성
- `app/md_pdf.py`: Markdown to PDF 변환
- `app/settlement.py`: 항목별 정산 계산기
- `app/idle_timeout.py`: 10분 비활성 창 닫기 시도
- `app/streamlit_compat.py`: Streamlit HTML/iframe 호환 렌더링 보조 함수
- `app/text_cleaner.py`: 텍스트 정리 로직 및 UI
- `app/access_logger.py`: 접속 로그 기록, 조회, 삭제
- `app/auth.py`: 관리자 비밀번호 확인 및 로그인 화면
- `app/core_utils.py`: 시간대, 파일명 정리, slug 변환 유틸
- `components/custom_copy_btn/`: 클립보드 복사용 커스텀 Streamlit 컴포넌트

---

## 기술 스택

- Python
- Streamlit
- Google Cloud Storage
- Google Auth
- Docker
- Google Cloud Build
- Google Cloud Run

---

## 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

MD to PDF 기능은 `weasyprint`가 사용하는 시스템 라이브러리도 필요합니다.

macOS 로컬 실행 환경:

```bash
brew install glib pango gdk-pixbuf libffi
```

Docker/Cloud Run 환경은 `Dockerfile`의 apt 패키지 설치 단계에서 처리합니다.

### 2. 로컬 설정

로컬에서는 `.streamlit/secrets.toml` 또는 환경변수를 사용해 설정할 수 있습니다.

예시:

```toml
admin_password = "YOUR_ADMIN_PASSWORD"

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
# Optional overrides
model = "gemini-3-flash-preview"
input_price_per_1m = 0.50
output_price_per_1m = 3.00
usd_to_krw_rate = 1478
```

### 3. 앱 실행

```bash
streamlit run jisong_cloud.py
```

---

## 환경 변수 및 설정 우선순위

### GCS 인증
`app/gcs_helper.py` 기준 우선순위:

1. `GCP_SERVICE_ACCOUNT_JSON`
2. `st.secrets["gcp_service_account"]`
3. Cloud Run ADC

### 버킷 이름
우선순위:

1. `GCS_BUCKET_NAME`
2. `st.secrets["gcs"]["bucket_name"]`

### 관리자 비밀번호
`app/auth.py` 기준 우선순위:

1. `ADMIN_PASSWORD`
2. `st.secrets["admin"]["admin_password"]`
3. `st.secrets["admin_password"]`

### Gemini API key
`app/ai.py` 기준 우선순위:

1. `GEMINI_API_KEY`
2. `st.secrets["gemini"]["api_key"]`

### Gemini 모델/비용 계산값
`app/ai.py` 기준으로 아래 환경변수 또는 `st.secrets["gemini"]` 값을 사용할 수 있습니다.

- `GEMINI_MODEL` / `model`
- `GEMINI_INPUT_PRICE_PER_1M` / `input_price_per_1m`
- `GEMINI_OUTPUT_PRICE_PER_1M` / `output_price_per_1m`
- `USD_TO_KRW_RATE` / `usd_to_krw_rate`

---

## Docker 실행

이 프로젝트는 `python:3.12-slim-bookworm` 기반 이미지를 사용합니다.

컨테이너 실행 시 Streamlit은 `0.0.0.0:8080`으로 열리도록 설정되어 있습니다.

```bash
docker build -t jisong-cloud .
docker run -p 8080:8080 jisong-cloud
```

---

## Cloud Run 배포

`cloudbuild.yaml` 기준으로 아래 흐름을 사용합니다.

1. Docker 이미지 빌드
2. Artifact Registry 푸시
3. Cloud Run 서비스 업데이트

현재 배포 설정에는 아래 항목이 포함되어 있습니다.

- 리전: `asia-northeast1`
- 서비스명: `jisong-cloud-tokyo`
- 환경변수: `GCS_BUCKET_NAME=jisong-cloud-storage`
- 시크릿: `ADMIN_PASSWORD=admin-password:1`
- 서비스 계정 지정 사용

---

## 의존성

현재 `requirements.txt` 기준:

- `streamlit`
- `google-cloud-storage`
- `google-auth`
- `pandas`
- `markdown`
- `weasyprint`
- `google-genai`

---

## 설계 방향

이 프로젝트는 아래 방향에 가깝습니다.

- 개인용 실사용 도구
- 단순한 구조 우선
- 기능 중심 개발
- GCS를 단일 영구 저장소로 활용
- Cloud Run 배포에 맞는 운영 방식
- 과도한 분리보다 빠른 유지보수 우선

---

## 한계 및 주의사항

- 현재 인증은 단일 관리자 비밀번호 기반입니다.
- 접속 로그는 JSON 파일 전체를 읽고 다시 쓰는 방식이라 동시성에 강한 구조는 아닙니다.
- 파일 다운로드는 현재 서버 메모리를 일부 사용하는 방식입니다.
- Gemini 분석은 API key와 외부 API 호출이 필요합니다.
- 자동 창 닫기는 브라우저 정책상 보장되지 않으며, 실패 시 안내 화면을 표시합니다.
- 일부 구버전 호환 로직(`memos.json` 마이그레이션)이 남아 있습니다.
- `.streamlit/` 같은 로컬 설정 디렉터리는 Git에 포함하지 않도록 관리합니다.

---

## 빠른 시작 체크리스트

1. GCS 버킷 준비
2. 관리자 비밀번호 설정
3. 서비스 계정 또는 ADC 구성
4. `pip install -r requirements.txt`
5. `streamlit run jisong_cloud.py`

이후 `웹하드`, `메모장`, `AI`, `도구모음` 메뉴를 통해 기능을 사용할 수 있습니다.
