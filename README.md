# Jisong Cloud

개인용 Streamlit 기반 미니 클라우드 앱입니다.

파일 업로드/다운로드, 간단한 메모 관리, 텍스트 정리 도구를 한곳에 모아 둔 개인 생산성 앱입니다.  
UI를 화려하게 만드는 것보다, 실제로 자주 쓰는 기능을 빠르게 처리하는 데 초점을 맞췄습니다.

현재 버전: 2.3

---

## 주요 기능

### 1. 웹하드
- 파일 업로드
- 저장된 파일 목록 조회
- 개별 다운로드
- 개별 삭제
- 전체 ZIP 다운로드
- 전체 삭제

저장소는 Google Cloud Storage(GCS)를 사용합니다.

### 2. 메모장
- 메모 작성
- 메모 수정
- 메모 삭제
- 개별 다운로드
- 전체 ZIP 다운로드
- 전체 삭제

메모는 GCS의 `memos/` prefix 아래 `.txt` 파일로 저장됩니다.  
본문은 lazy loading 방식으로 불러와서, 메모 수가 많아져도 목록 로딩이 과하게 느려지지 않도록 구성했습니다.

### 3. 도구모음
현재 포함된 도구:
- 텍스트 클리너
- 글자수 카운터
- 오늘 뭐 먹지?

#### 텍스트 클리너
- 탭 제거
- 연속 공백 정리
- 연속 빈 줄 정리
- 각 줄 앞뒤 공백 제거
- 줄번호 제거
- URL 제거
- 특수문자 제거
- 줄바꿈 병합

#### AI mode
AI 답변이나 복붙 텍스트를 Markdown 친화적으로 정리하기 위한 프리셋입니다.

예:
- `•`, `·`, `○`, `◦`, `▪`, `*` 등을 `- `로 통일
- `---`, `⸻`, `***`, `___` 같은 구분선 제거
- 불필요한 공백 정리
- 필요 시 번호 리스트도 `- `로 변환 가능

---

## 프로젝트 구조

```text
.
├── jisong_cloud.py     # 진입점 / 사이드바 / 라우팅 / 접속 로그
├── storage.py          # 파일 업로드/조회/삭제/GCS 연동
├── memo.py             # 메모 CRUD / lazy loading / GCS 연동
├── tools.py            # 도구모음 UI
├── text_cleaner.py     # 텍스트 클리너
├── core_utils.py       # 공통 유틸 / 시간 / 파일명 / GCS helper
└── requirements.txt
```

---

## 기술 스택
- Python
- Streamlit
- Google Cloud Storage
- google-auth

---

## 저장 구조

GCS 버킷 1개를 사용하고, 내부 prefix만 나눠서 관리합니다.

```text
bucket/
├── uploads/
│   └── ...
├── memos/
│   └── ...
└── logs/
    └── access_log.json
```

### uploads/
업로드된 일반 파일 저장

### memos/
메모 `.txt` 파일 저장

메모 파일은 대략 아래 형식을 가집니다.

```text
TITLE: 메모 제목
CREATED_AT: 2026-04-10 20:31:00
UPDATED_AT: 2026-04-10 20:45:12

여기부터 본문...
```

또한 GCS blob metadata에도 일부 정보를 저장하여, 메모 목록은 본문 전체를 매번 읽지 않고 표시할 수 있도록 구성했습니다.

### logs/access_log.json
마지막 접속 기록 저장

---

## 캐시 전략

GCS를 직접 사용하면 로컬 파일 기반보다 느릴 수 있기 때문에, 현재 버전에서는 다음과 같은 캐시 전략을 사용합니다.

- GCS client: `st.cache_resource`
- 파일 목록: `st.cache_data(ttl=30)`
- 메모 목록: `st.cache_data(ttl=30)`
- 메모 본문: 필요할 때만 lazy loading
- 저장/삭제 후에는 관련 캐시를 직접 clear

즉:
- 원본 데이터는 GCS
- 목록 조회는 캐시
- 메모 본문은 열 때만 로드

이 구조로 속도와 단순성을 적당히 타협했습니다.

---

## 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. Streamlit secrets 설정

로컬에서는 아래 경로에 설정합니다.

```text
.streamlit/secrets.toml
```

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
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CLIENT_X509_CERT_URL"
universe_domain = "googleapis.com"
```

### 3. 실행

```bash
streamlit run jisong_cloud.py
```

---

## GCS 설정 요약

필요한 준비:
- Google Cloud 프로젝트 생성
- Billing 연결
- Cloud Storage API 활성화
- 버킷 생성
- 서비스 계정 생성
- 서비스 계정에 버킷 권한 부여
- 서비스 계정 JSON 키 발급
- Streamlit secrets에 등록

권장 구조:
- 버킷 1개
- `uploads/`, `memos/`, `logs/` prefix 사용
- 버킷은 private 유지
- 앱이 서비스 계정으로 직접 접근

사용자 로그인은 필요하지 않습니다.  
현재 구조는 “사이트 사용자는 로그인 없이 사용하고, 앱 서버만 GCS에 접근”하는 방식입니다.

---

## 설계 방향

이 프로젝트는 다음 원칙을 따릅니다.

- 개인용 실사용 도구
- 과한 아키텍처 분리 지양
- 유지보수 부담 최소화
- UI보다 기능 우선
- 로컬 개발 + Streamlit 배포에 적합한 구조
- GCS를 영구 저장소로 사용하되, 캐시로 체감 속도 보완

즉, “예쁜 서비스”보다는 “자주 쓰는 작은 도구를 안정적으로 모아둔 개인 작업앱”에 가깝습니다.

---

## 현재 한계

- GCS 기반이라 로컬 파일 기반보다 업로드/다운로드가 약간 느릴 수 있음
- 파일 검색, 태그, 폴더 계층 같은 고급 기능은 없음
- 협업용 서비스가 아니라 개인용에 최적화되어 있음
- 메모 편집기는 단순 텍스트 기반
- UI는 기능 중심으로 최소 구성

---

## 향후 개선 후보

우선순위는 낮지만, 필요하면 나중에 추가할 수 있는 것들:

- 파일/메모 검색
- 메모 태그
- 최근 사용 항목
- 즐겨찾기
- 간단한 정렬 옵션
- 텍스트 클리너 preset 확장
- 에러 메시지 정리
- 메모 메타데이터 마이그레이션 보조 함수

현재 버전에서는 여기까지는 굳이 하지 않고, 실제 사용성을 우선합니다.

---

## 버전 메모

### v2.3
- GCS 저장 구조 도입
- 파일/메모를 GCS 버킷 1개로 통합 관리
- 파일 목록 캐시 추가
- 메모 목록 캐시 추가
- 메모 본문 lazy loading 적용
- 텍스트 클리너에 AI mode 추가
- 전체 구조를 개인용 실사용 버전으로 정리

---

## 한 줄 설명

Jisong Cloud는  
“파일, 메모, 텍스트 정리를 한곳에 모은 개인용 Streamlit 작업앱”입니다.
