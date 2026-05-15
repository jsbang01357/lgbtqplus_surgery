# Jisong Cloud Frontend

`DESIGN.md`의 Apple식 UI 언어를 반영한 새 정적 프론트엔드입니다.

현재 프론트엔드는 `api_server.py`가 정적 파일로 제공하며, 파일, 메모, AI, 도구 화면은 `/api/*` endpoint를 통해 GCS/Gemini 로직과 연결됩니다. 운영 기준은 GCP 프로젝트이며 Cloudflare Access와 패스키 인증을 기본 경계로 둡니다.

## 실행

```bash
uvicorn api_server:app --host 127.0.0.1 --port 8080
```

브라우저에서 `http://127.0.0.1:8080`을 엽니다.

## 구조

- `index.html`: 앱 마크업
- `styles.css`: Apple 스타일 디자인 토큰과 반응형 레이아웃
- `app.js`: 인증 상태, 파일/메모 CRUD, AI 분석, 도구모음 상호작용

## 연결 메모

- 파일 업로드/삭제/다운로드는 `app/storage.py` 로직을 Starlette API로 감싸 연결합니다.
- 메모 CRUD는 `app/memo.py` 로직을 Starlette API로 감싸 연결합니다.
- AI 분석은 `app/ai.py`의 Gemini 비용 제한 흐름을 유지한 채 `/api/ai/analyze` endpoint로 연결합니다.
- 인증은 Cloudflare Access를 외부 관문으로 두고, 앱 내부 민감 작업은 WebAuthn 패스키로 보호합니다.
