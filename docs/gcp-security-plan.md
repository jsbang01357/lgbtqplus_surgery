# GCP 보안 전환 계획

Jisong Cloud의 운영 기준은 GCP 프로젝트입니다. Mac mini 로컬 Docker 호스팅과 로컬 LLM 경로는 제거하고, Cloud Run + GCS + Gemini + Cloudflare Access + 패스키 인증을 기본 경계로 둡니다.

## 목표 구조

```text
User
└── Cloudflare Access
    └── Cloud Run
        ├── Jisong Cloud API / UI
        ├── GCS
        ├── Gemini API
        └── Secret Manager
```

## 인증 경계

- Cloudflare Access: `cloud.jisong.dev` 앞단의 외부 접근 제어
- 패스키 인증: 앱 내부 민감 작업 보호
- 관리자 비밀번호: 패스키 전환 전까지만 유지할 임시 fallback

## 패스키 구현 메모

- 서버는 challenge를 발급하고 세션에 저장한다.
- 브라우저는 WebAuthn `navigator.credentials.create()` / `navigator.credentials.get()`을 호출한다.
- 서버는 credential public key, sign count, user handle을 저장한다.
- 민감 작업은 Cloudflare Access 통과 여부와 패스키 세션을 모두 확인한다.

## 제거된 경로

- Mac mini Docker Compose 운영
- launchd 로컬 자동 기동
- local mirror 저장소 adapter
- Ollama/local LLM provider와 fallback

## 다음 구현 순서

1. 새 프론트엔드용 Python API 경계 생성
2. Cloudflare Access 헤더 검증 middleware 추가
3. 패스키 등록/로그인 API 추가
4. 관리자 비밀번호 fallback을 제한적으로 유지
5. Cloud Run 배포 후 Access 정책과 앱 내부 인증을 함께 검증

## 환경 변수

- `REQUIRE_CLOUDFLARE_ACCESS=false`: Cloudflare Access 이메일 OTP를 피하기 위해 기본 필수 조건에서는 제외한다.
- `CLOUDFLARE_ACCESS_ALLOWED_EMAILS=jsbang01357@gmail.com`: 소유자 Google 계정만 허용한다. 값을 비워도 앱 기본값은 `jsbang01357@gmail.com`이다.
- `ALLOW_ACCOUNT_ID_FALLBACK=true`: 패스키를 쓸 수 없는 브라우저에서는 소유자 계정 ID 세션으로 통과시킨다.
- `JISONG_ACCOUNT_LOGIN_ID=jsbang01357@gmail.com`
- `JISONG_ACCOUNT_PASSWORD`: 계정 ID fallback 비밀번호
- `PASSKEY_RP_ID=cloud.jisong.dev`
- `PASSKEY_ORIGIN=https://cloud.jisong.dev`
- `PASSKEY_RP_NAME=Jisong Cloud`

## Cloudflare CLI 메모

- 현재 로컬에는 `cloudflared`가 설치되어 있으며 Tunnel/Access 관련 확인에 사용할 수 있다.
- `wrangler`는 현재 PATH에 없으므로 Workers/Pages 작업이 필요할 때 별도로 설치한다.
- Cloud Run 앞단 Access 정책은 `jsbang01357@gmail.com`만 허용하도록 Cloudflare dashboard 또는 API에서 맞춘다.
