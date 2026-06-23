# GCP 선택 운영 보안 계획

Qplus Surgery의 기본 운영 기준은 오프라인 로컬 저장소입니다. 이 문서는 GCS/Cloud Run/Cloudflare Access로 전환할 때만 사용하는 보안 체크리스트입니다.

## 전환 조건

GCP 운영은 아래 조건이 충족될 때만 고려합니다.

- 내부망 단독 운영보다 원격 접근 필요성이 명확하다.
- 환자/수술 운영 데이터의 외부 저장 정책이 승인되어 있다.
- Cloudflare Access 또는 동등한 접근 제어를 적용한다.
- Secret Manager 또는 안전한 환경변수 관리가 준비되어 있다.
- 백업/감사/삭제 정책이 문서화되어 있다.

## 목표 구조

```text
User
└── Cloudflare Access
    └── Cloud Run
        ├── Qplus Surgery API/UI
        ├── GCS
        └── optional Google Calendar
```

## 필수 환경변수

```env
STORAGE_BACKEND="gcs"
OFFLINE_MODE="false"
GCS_BUCKET_NAME="lgbtqplus-surgery"
REQUIRE_CLOUDFLARE_ACCESS="true"
CLOUDFLARE_ACCESS_ALLOWED_EMAILS="허용이메일"
ALLOW_ACCOUNT_ID_FALLBACK="true"
ALLOW_PUBLIC_REGISTRATION="false"
```

서비스 계정:

```env
GCP_SERVICE_ACCOUNT_JSON="..."
```

또는 Cloud Run의 기본 서비스 계정/ADC를 사용합니다.

## 접근 제어

- Cloudflare Access에서 허용 이메일을 제한합니다.
- 앱 내부에서도 passkey 또는 계정 세션을 요구합니다.
- 공개 회원가입은 유지하지 않습니다.
- `viewer`, `staff`, `admin` 역할을 분리합니다.

## 저장소 권한

서비스 계정은 필요한 bucket에만 접근합니다.

권장 최소 권한:

- GCS object read/write/delete
- 필요한 bucket 단위로 제한
- Secret 접근은 필요한 secret만 제한

## Calendar 사용 시 주의

Google Calendar는 선택 기능입니다.

켜는 경우:

```env
GOOGLE_CALENDAR_SYNC_ENABLED="true"
GOOGLE_CALENDAR_ID="..."
GDRIVE_CLIENT_ID="..."
GDRIVE_CLIENT_SECRET="..."
GDRIVE_REDIRECT_URI="https://서비스도메인/api/auth/gdrive/callback"
```

외부 캘린더에는 넣지 않을 정보:

- 환자명
- 선호이름
- 진단명
- 상세 비고
- 프리메드 상세
- 과거력/복용약/검사 이상 세부 내용

## 배포 전 체크리스트

- [ ] 저장소 백엔드가 `gcs`인지 확인
- [ ] `OFFLINE_MODE=false` 확인
- [ ] Cloudflare Access 강제 여부 확인
- [ ] 공개 회원가입 비활성화 확인
- [ ] Secret 값이 git에 없는지 확인
- [ ] 테스트 계정으로 로그인 확인
- [ ] CSV export/import 확인
- [ ] Calendar 동기화가 필요한 정보만 보내는지 확인
- [ ] 롤백 기준 문서화

## 롤백

클라우드 전환 중 문제가 생기면:

1. Cloud Run 트래픽을 이전 revision으로 되돌립니다.
2. GCS의 `surgery_ops/cases/`를 백업합니다.
3. 필요하면 데이터를 `.local_data/storage/` 구조로 내려받아 오프라인 모드로 복구합니다.
