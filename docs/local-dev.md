# 로컬 개발 및 검증

이 문서는 Qplus Surgery 개발자가 로컬에서 앱을 실행하고 검증하는 기준입니다.

## Python 환경

권장 버전:

- Python 3.12 또는 3.13

설치:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## 설정

```bash
cp .env.example .env
```

개발 기본값:

```env
STORAGE_BACKEND="local"
OFFLINE_MODE="true"
LOCAL_STORAGE_ROOT=".local_data/storage"
REQUIRE_CLOUDFLARE_ACCESS="false"
ALLOW_ACCOUNT_ID_FALLBACK="true"
GOOGLE_CALENDAR_SYNC_ENABLED="false"
```

## 서버 실행

내 컴퓨터에서만 볼 때:

```bash
.venv/bin/uvicorn api_server:app --host 127.0.0.1 --port 8080 --reload
```

내부망 다른 PC에서도 볼 때:

```bash
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8080 --reload
```

## 빠른 검증

```bash
.venv/bin/python -m unittest tests/python/test_config.py tests/python/test_gcs.py tests/python/test_surgery_status.py
node --check frontend/app.js
.venv/bin/python -m py_compile api_server.py app/*.py app/routers/*.py
```

## 전체 Python 테스트

```bash
.venv/bin/python -m unittest discover -s tests/python
```

외부 서비스와 연결되는 테스트는 환경에 따라 느릴 수 있습니다. 빠른 회귀 확인은 위의 빠른 검증 세트를 우선 사용합니다.

## parser-core

현재 수술 대시보드 운영에는 parser-core가 필수 경로가 아닙니다. TypeScript 코어를 검증할 때만 아래 명령을 실행합니다.

```bash
npm --prefix parser-core ci
npm --prefix parser-core run check
```

## 문법 검사

```bash
node --check frontend/app.js
.venv/bin/python -m py_compile api_server.py app/*.py app/routers/*.py
```

## 데이터 초기화

개발 데이터만 지우려면 서버를 끈 뒤 `.local_data/storage/`를 백업하고 새 폴더로 시작합니다.

주의: 운영 데이터가 들어간 폴더는 삭제하지 않습니다.
