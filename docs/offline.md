# 오프라인 운영 가이드

이 문서는 Qplus Surgery를 맥미니 또는 내부망 PC에서 오프라인 우선 서비스로 운영하는 기준입니다.

## 운영 목표

- 외래/수술 관련 사용자가 내부망에서 접속한다.
- 수술 일정 데이터는 로컬 디스크에 저장한다.
- GCS, Cloud Run, Google Calendar가 없어도 기본 기능이 동작한다.
- 백업과 복구는 `.local_data/storage/` 폴더 단위로 처리한다.

## 1. 설치

```bash
cd ~/Developer/lgbtqplus_surgery
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
cp .env.example .env
```

## 2. `.env` 설정

오프라인 기본값:

```env
STORAGE_BACKEND="local"
OFFLINE_MODE="true"
LOCAL_STORAGE_ROOT=".local_data/storage"
GOOGLE_CALENDAR_SYNC_ENABLED="false"
REQUIRE_CLOUDFLARE_ACCESS="false"
ALLOW_ACCOUNT_ID_FALLBACK="true"
ALLOW_GOOGLE_AUTH_FALLBACK="false"
ALLOW_PUBLIC_REGISTRATION="false"
```

운영 전 반드시 수정:

```env
JISONG_OWNER_EMAIL="운영자이메일"
JISONG_ACCOUNT_LOGIN_ID="운영자이메일"
ADMIN_PASSWORD="긴-초기-관리자-비밀번호"
PASSKEY_RP_ID="맥미니IP"
PASSKEY_ORIGIN="http://맥미니IP:8080"
```

예시:

```env
PASSKEY_RP_ID="192.168.0.35"
PASSKEY_ORIGIN="http://192.168.0.35:8080"
```

## 3. 실행

```bash
source .venv/bin/activate
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8080
```

확인:

- 맥미니: `http://127.0.0.1:8080`
- 내부망 PC: `http://맥미니IP:8080`

`--host 0.0.0.0`을 써야 다른 내부망 PC에서 접속할 수 있습니다.

## 4. 데이터 저장 구조

```text
.local_data/storage/
├── surgery_ops/cases/
├── surgery_ops/audit/
├── auth/
└── logs/
```

중요 파일:

- `surgery_ops/cases/case_*.json`: 수술 케이스
- `surgery_ops/audit/surgery_ops_audit.jsonl`: 저장/삭제/취소 감사 로그
- `auth/users.json`: 등록 사용자
- `auth/account_sessions.json`: 로그인 세션
- `auth/passkeys.json`: passkey credential/session
- `logs/access_log.json`: 접속 로그

## 5. 백업

서버를 잠시 멈춘 뒤 아래 폴더를 복사합니다.

```bash
cp -R .local_data/storage ~/qplus-surgery-backup/storage-$(date +%Y%m%d-%H%M%S)
```

운영 권장:

- 매일 1회 외부 디스크 또는 병원 내부 백업 위치로 복사
- CSV export도 주기적으로 내려받기
- 백업에는 인증 파일이 포함되므로 접근 권한을 제한

## 6. 복구

1. 서버를 중지합니다.
2. 기존 `.local_data/storage`를 별도 이름으로 보관합니다.
3. 백업한 `storage` 폴더를 `.local_data/storage`로 복사합니다.
4. 서버를 다시 실행합니다.

```bash
mv .local_data/storage .local_data/storage-broken-$(date +%Y%m%d-%H%M%S)
cp -R ~/qplus-surgery-backup/storage-YYYYMMDD-HHMMSS .local_data/storage
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8080
```

## 7. 계정 운영

기본 정책:

- 공개 회원가입 비활성화
- 운영자 계정은 `.env`의 `JISONG_ACCOUNT_LOGIN_ID`와 `ADMIN_PASSWORD`로 시작
- 일반 계정은 운영자가 별도 등록/관리하는 방향 권장

현재 역할:

- `admin`: 전체 관리
- `staff`: 수술 케이스 생성/수정/삭제
- `viewer`: 조회 중심

## 8. Google Calendar

오프라인 운영에서는 기본 비활성화입니다.

```env
GOOGLE_CALENDAR_SYNC_ENABLED="false"
```

이 상태에서는:

- Calendar 상태 API가 `offline`으로 응답합니다.
- 프론트엔드에 Google 연동 버튼이 표시되지 않습니다.
- 케이스 저장 시 외부 네트워크를 호출하지 않습니다.

## 9. 검증

```bash
.venv/bin/python -m unittest tests/python/test_config.py tests/python/test_gcs.py tests/python/test_surgery_status.py
node --check frontend/app.js
.venv/bin/python -m py_compile api_server.py app/*.py app/routers/*.py
```

## 10. 문제 대응

로그인이 안 됨:

- `.env`의 `ALLOW_ACCOUNT_ID_FALLBACK=true` 확인
- `JISONG_ACCOUNT_LOGIN_ID`, `ADMIN_PASSWORD` 확인
- 브라우저 쿠키 삭제 후 재시도

내부망 PC에서 접속 안 됨:

- 서버 실행 옵션이 `--host 0.0.0.0`인지 확인
- 맥미니 IP 확인
- 방화벽 또는 병원망 정책 확인

데이터가 안 보임:

- `STORAGE_BACKEND=local` 확인
- `LOCAL_STORAGE_ROOT` 경로 확인
- `.local_data/storage/surgery_ops/cases/`에 JSON 파일이 있는지 확인

캘린더 연동이 안 됨:

- 오프라인 기본값에서는 정상입니다.
- Calendar를 쓰려면 `GOOGLE_CALENDAR_SYNC_ENABLED=true`로 별도 전환해야 합니다.
