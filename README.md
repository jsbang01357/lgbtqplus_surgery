# Jisong Cloud

개인용 Streamlit 기반 미니 클라우드 앱입니다.

파일 업로드/다운로드, 간단한 메모 관리, 텍스트 정리 도구를 한곳에 모아 둔 개인 생산성 앱입니다.  
UI를 화려하게 만드는 것보다, 실제로 자주 쓰는 기능을 빠르게 처리하는 데 초점을 맞췄습니다.

현재 버전: 2.4

---

## 주요 기능

### 1. 웹하드
- 파일 업로드
- 저장된 파일 목록 조회
- **Lazy Download 적용**: 서버 메모리를 절약하기 위해, 다운로드 시 GCS 직접 링크(Signed URL) 이용
- 개별 다운로드 및 삭제
- 예약형 전체 ZIP 생성 및 다운로드
- 전체 삭제

저장소는 Google Cloud Storage(GCS)를 사용합니다.

### 2. 메모장
- 메모 작성 / 수정 / 삭제
- 개별 다운로드
- 예약형 전체 ZIP 생성 및 다운로드
- 전체 삭제

메모는 GCS의 `memos/` prefix 아래 `.txt` 파일로 저장됩니다.  
본문은 lazy loading 방식으로 불러와서, 메모 수가 많아져도 목록 로딩이 과하게 느려지지 않도록 구성했습니다.

### 3. 도구모음
현재 포함된 도구:
- 텍스트 클리너 (기본 정리, AI mode Markdown 정리)
- 글자수 카운터
- 오늘 뭐 먹지?
- **접속 기록 관리**: 누적 접속자 로그(IP, 브라우저 정보, 500건 한도) 관리 및 보안 삭제 기능(비밀번호 필요)

---

## 프로젝트 구조

```text
.
├── jisong_cloud.py        # 메인 진입점 / 사이드바 구성 및 라우팅
├── app/                   # 핵심 기능 모듈
│   ├── gcs_helper.py      # GCS 클라이언트 인증 및 환경 변수 우선 적용
│   ├── storage.py         # 파일 업로드/조회/삭제 및 Signed URL 다운로드 처리
│   ├── memo.py            # 메모 CRUD 기능
│   ├── tools.py           # 도구모음 및 접속 기록 관리 UI
│   ├── text_cleaner.py    # 텍스트 클리너 및 AI 정리 프리셋
│   ├── access_logger.py   # IP, 접속 브라우저 기록 로깅 및 조회 모듈
│   └── core_utils.py      # 공통 유틸 / 시간 / 텍스트 클리닝 처리
├── components/            # UI 확장 컴포넌트 모음
│   └── custom_copy_btn/   # 자체 제작 클립보드 복사 버튼
├── data/
│   └── menu_list.json     # 메뉴 랜덤 선택을 위한 로컬 JSON
├── .streamlit/            # 로컬 배포 테스트용 비밀 설정 (secrets.toml)
├── Dockerfile             # 컨테이너화 정보 (Debian-based python 이미지)
├── cloudbuild.yaml        # GCP Cloud Build/Cloud Run CI/CD 파이프라인
└── requirements.txt       # 프로젝트 구동 의존성
```

---

## 기술 스택
- Python
- Streamlit
- Google Cloud Storage (google-cloud-storage)
- Google Auth (google-auth)
- Docker & Cloud Run

---

## 저장 및 캐시 다운로드 구조

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

### logs/access_log.json
IP 주소와 User-Agent가 포함된 최근 500건의 상세 접속 기록이 누적되어 리스트 형태로 관리됩니다.

### 다운로드 (Lazy Download) 로직
파일 목록을 불러올 때는 메타데이터만 쿼리하고, Streamlit 서버로 파일 전체를 불러와 버튼에 싣지 않습니다. 파일별 **GCS 다운로드용 임시 링크(Signed URL)**를 생성해서 버튼을 제공하며, 파일이 크더라도 Streamlit 서버의 부하 없이 빠르게 화면이 뜨고 브라우저에서 GCS로부터 다이렉트로 안전하게 다운로드합니다. 일괄 압축 파일의 경우, 사용자가 "ZIP 준비하기"를 눌렀을 때만 압축을 수행합니다.

---

## 실행 및 배포 방법

### 1. 패키지 설치 (로컬 개발 시)

```bash
pip install -r requirements.txt
```

### 2. Streamlit secrets 설정 (로컬 환경)

로컬 폴더 내 `.streamlit/secrets.toml` 파일에 기록하여 사용합니다:

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
...
```

### 3. Cloud Run 배포 (운영 환경)

이 프로젝트는 Dockerfile과 Google Cloud Build를 통해 **Cloud Run**으로 완전 자동 배포되도록 구성되어 있습니다 (`cloudbuild.yaml`).

서비스 구동에 필요한 인증키나 권한 정보는 다음 중 유리한 방식을 자동으로 택해 호환됩니다:
- **Cloud Run Application Default Credentials (ADC)**
- `GCP_SERVICE_ACCOUNT_JSON` 환경 변수 문자열
- 로컬 `st.secrets` 에 있는 서비스 계정 데이터

또한 `GCS_BUCKET_NAME` 및 로그 삭제 비밀번호 `ADMIN_PASSWORD` 환경 변수를 Cloud Run에 주입하여 동작 환경을 안전하게 분리할 수 있습니다.

---

## 설계 방향

이 프로젝트는 다음 원칙을 따릅니다.

- 개인용 실사용 도구
- 과한 아키텍처 분리 지양
- 유지보수 부담 최소화
- UI보다 기능 우선, 리소스 최적화 구조 도입 
- 로컬 개발 + Dockerized 배포(Cloud Run)에 적합한 구조
- GCS를 영구 저장소로 사용하되, 메모리 이슈를 일으키지 않는 (메타데이터 조회/Signed URL 활용) 캐싱 전략 도입

---

## 버전 메모

### v2.4 (최신)
- 구조 분리 및 패키지화 (`app/`, `components/`, `data/`) 전면 적용
- Docker 컨테이너 및 GCP Cloud Build, Cloud Run(`cloudbuild.yaml`) 연동 설정
- **Lazy Download** 전략 도입:
    - 다운로드 시 임시 보안 링크(Signed URL) 다이렉트 제공
    - 일괄 압축 기능의 분리 (수동 준비 시스템)
- 도구모음에 관리자 검증(`ADMIN_PASSWORD`) 기반의 '접속 기록 관리' UI 탑재
- 누적형 고도화 로깅 추가 (최대 500건, IP 및 브라우저 정보 수집)

### v2.3
- GCS 저장 구조 도입
- 파일 목록/메모 목록 캐시 추가 및 본문 lazy loading 적용
