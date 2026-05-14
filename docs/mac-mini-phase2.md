# Mac mini 병행 서버 Phase 2+

목표는 같은 GitHub repo로 `cloud.jisong.dev` Cloud Run 운영을 유지하면서, `mac.jisong.dev`를 Mac mini Docker + Cloudflare Tunnel로 병행 가동하는 것이다. Tailscale은 사용하지 않는다.

## 구성

```text
Mac mini
├── Docker
│   ├── jisong-cloud-local
│   └── jisong-cloudflared
└── Ollama
    ├── gemma4:e4b
    └── qwen3.5:9b
```

외부 진입은 Cloudflare Tunnel이 받고, 앱 컨테이너는 로컬 루프백 `127.0.0.1:8501`에만 포트를 연다. GCS는 공통 버킷을 사용하므로 `cloud.jisong.dev`와 `mac.jisong.dev`의 파일/메모 데이터는 같은 저장소를 본다.

## 로컬 저장소 + GCS mirror

Mac mini 운영은 `STORAGE_BACKEND=local_mirror`를 기본값으로 둔다.

```text
/Users/jsbang/jisong-data/storage
├── uploads/
├── memos/
└── logs/
```

앱 컨테이너 안에서는 위 경로가 `/data/jisong-cloud`로 mount된다. 읽기는 로컬 디스크를 우선 사용하고, 목록 조회 시 GCS에서 새 파일을 내려받는다. 업로드, 메모 저장, 로그 저장, 삭제는 로컬에 먼저 반영한 뒤 GCS에도 mirror한다.
목록 조회와 도구모음의 `저장소 상태` 수동 동기화는 로컬에만 남은 파일을 GCS로 다시 올리는 reconcile도 함께 수행한다.

운영 모드:

- `STORAGE_BACKEND=gcs`: 기존 Cloud Run 방식
- `STORAGE_BACKEND=local`: Mac mini 로컬 디스크만 사용
- `STORAGE_BACKEND=local_mirror`: Mac mini 로컬 디스크 + GCS 동기화

`mac.jisong.dev`는 `local_mirror`, `cloud.jisong.dev`는 `gcs`를 권장한다.

## 실행 준비

1. Mac mini에서 이 repo를 최신 상태로 둔다.
2. `/Users/jsbang/jisong-data/secrets/gcp-service-account.json` 같은 고정 경로에 GCS 서비스 계정 JSON을 둔다.
3. `.env.local.example`을 기준으로 `.env.local`을 만든다.
4. Cloudflare Zero Trust에서 Tunnel token을 발급해 `CLOUDFLARED_TOKEN`에 넣는다.

```bash
docker compose --env-file .env.local -f docker-compose.local.yml up -d --build
```

앱만 확인할 때:

```bash
curl -I http://127.0.0.1:8501
docker compose --env-file .env.local -f docker-compose.local.yml logs -f jisong-cloud
```

## Cloudflare Tunnel

Public hostname:

```text
mac.jisong.dev -> http://jisong-cloud:8080
```

`cloudflared`와 앱이 같은 Compose network 안에 있으므로 Cloudflare dashboard의 service URL은 Docker service name인 `http://jisong-cloud:8080`을 우선 사용한다. dashboard에서 host 연결이 불안정하면 `http://host.docker.internal:8501`로 바꿔 테스트한다.

현재 compose는 Cloudflare dashboard의 `http://localhost:8501` 설정도 그대로 동작하도록 `cloudflared`를 `jisong-cloud` 컨테이너와 같은 network namespace에서 실행한다. 그래서 `cloudflared` 컨테이너 입장의 `localhost:8501`이 Streamlit 앱을 가리킨다.

Cloud Run에서도 Mac mini Ollama를 fallback으로 쓰려면 Ollama API도 Tunnel 뒤에 별도 hostname으로 노출한다.

```text
ai.mac.jisong.dev -> http://host.docker.internal:11434
```

이 hostname은 브라우저 로그인용이 아니라 Cloud Run 서버가 호출하는 내부 API로 본다. Cloudflare Access에서 Service Token을 만들고, Cloud Run에는 아래 환경변수를 Secret Manager 또는 환경변수로 넣는다.

```text
AI_PROVIDER=auto
AI_FALLBACK_PROVIDER=gemini
OLLAMA_BASE_URL=https://ai.mac.jisong.dev
OLLAMA_MODEL=gemma4:e4b
OLLAMA_MODEL_OPTIONS=gemma4:e4b,qwen3.5:9b
OLLAMA_CF_ACCESS_CLIENT_ID=...
OLLAMA_CF_ACCESS_CLIENT_SECRET=...
```

이렇게 하면 Cloud Run의 AI 화면에서도 Ollama를 먼저 시도하고, Mac mini/Ollama/Tunnel이 죽어 있으면 Gemini로 이어서 분석한다.

## Access 정책

Cloudflare Access 앱은 `cloud.jisong.dev`, `mac.jisong.dev`, `ai.mac.jisong.dev`에 같은 원칙으로 건다. Cloudflare Access는 명시적으로 허용되지 않은 사용자를 기본 차단하는 구조라, 아래처럼 정책을 분리한다.

- `학교 고정 IP`: Allow, Include IP ranges에 학교 컴퓨터 공인 IP/CIDR 등록
- `내 계정`: Allow, Include emails에 `me@jisong.dev` 등록
- `관리 기기`: Apple 기기 패스키/기기 신뢰는 Cloudflare Zero Trust의 identity provider 및 device posture로 묶어 별도 Allow 정책에 둔다
- `Cloud Run -> Ollama`: Service Auth, Cloudflare Access service token으로 `ai.mac.jisong.dev`만 통과

학교 고정 IP는 Access를 완전히 Bypass하지 말고 Allow 정책으로 두는 쪽이 낫다. 그래야 Access 로그가 남고, 앱 내부 관리자 비밀번호도 한 번 더 확인한다.

## 앱 내부 인증

Cloudflare Access는 외부 문지기이고, Streamlit 앱의 `ADMIN_PASSWORD`는 내부 작업 보호용으로 유지한다.

- 인증된 Apple 기기: Cloudflare Access에서 통과. 기존에 신뢰된 기기는 Cloudflare 세션과 device posture 정책으로 재인증 빈도를 낮춘다.
- 학교 컴퓨터: 고정 IP Allow 후 앱 관리자 비밀번호 입력
- 그 외 장소: `me@jisong.dev` 계정으로 Cloudflare Access 로그인 후 앱 접근

기존 Cloud Run의 `cloud.jisong.dev`는 그대로 유지하되, Access 정책은 `mac.jisong.dev`와 맞춰 둔다.

## Ollama AI 모드

Mac mini에서 Ollama가 host로 떠 있으면 컨테이너 안에서는 기본적으로 아래 주소를 사용한다.

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

앱 AI 화면에서 `Gemini` 또는 `Ollama (Mac mini)`를 선택할 수 있다. Ollama 모드는 메모, 직접 입력 텍스트, TXT/MD/CSV, DOCX/XLSX/PPTX에서 추출한 텍스트를 분석한다. PDF와 이미지는 Gemini처럼 원본 업로드 분석을 하지 않는다.

로컬에서 연결 확인:

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

컨테이너에서 연결 확인:

```bash
docker compose --env-file .env.local -f docker-compose.local.yml exec jisong-cloud python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=5).read().decode())"
```

로컬 저장소 확인:

```bash
find /Users/jsbang/jisong-data/storage -maxdepth 3 -type f
```

앱 안에서는 `도구모음 -> 저장소 상태`에서 backend, 로컬 파일 수, GCS 파일 수를 확인하고 `지금 동기화`를 누를 수 있다.

## 안정성 테스트

- Mac mini 재부팅 후 Docker 컨테이너 자동 복구
- Wi-Fi 끊김 뒤 Tunnel 자동 복구
- `mac.jisong.dev` 접속 속도
- `cloud.jisong.dev`에서 `ai.mac.jisong.dev` Ollama fallback 호출
- GCS 업로드/다운로드/메모 저장
- 로컬 저장소 `uploads/`, `memos/`, `logs/` 생성 여부
- Gemini 모드와 Ollama 모드 각각 분석
- Cloudflare Access 로그와 앱 접속 로그
