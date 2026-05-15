# Jisong Cloud Frontend

`DESIGN.md`의 Apple식 UI 언어를 반영한 새 정적 프론트엔드입니다.

현재 프론트엔드는 `api_server.py`가 정적 파일로 제공하며, 파일, 메모, AI, 도구 화면은 `/api/*` endpoint를 통해 GCS/Gemini 로직과 연결됩니다. 운영 기준은 GCP 프로젝트이며 패스키와 계정 ID fallback을 앱 인증 경계로 둡니다.

## 실행

```bash
uvicorn api_server:app --host 127.0.0.1 --port 8080
```

브라우저에서 `http://127.0.0.1:8080`을 엽니다.

## 구조

- `index.html`: 앱 마크업
- `partials/home.html`: 홈 hero와 workspace 지표
- `partials/files.html`: 웹하드 화면
- `partials/memos.html`: 메모장 화면
- `partials/ai.html`: AI 분석 화면
- `partials/tools.html`: 도구모음 화면
- `partials/settings.html`: 계정 ID 로그인, 접속 기록, Gemini 사용량 설정 화면
- `styles.css`: Apple 스타일 디자인 토큰과 반응형 레이아웃
- `app.js`: 인증 상태, 파일/메모 CRUD, AI 분석, 도구모음 상호작용

`index.html`에는 `<!-- include:partials/*.html -->` 주석이 있고, `api_server.py`가 요청 시 partial을 조립해 완성된 HTML을 내려줍니다.

## 연결 메모

- 파일 업로드/삭제/다운로드는 `app/storage.py` 로직을 Starlette API로 감싸 연결합니다.
- 메모 CRUD는 `app/memo.py` 로직을 Starlette API로 감싸 연결합니다.
- AI 분석은 `app/ai.py`의 Gemini 비용 제한 흐름을 유지한 채 `/api/ai/analyze` endpoint로 연결합니다.
- 인증은 WebAuthn 패스키를 우선 사용하고, 패스키가 어려운 환경에서는 소유자 계정 ID fallback으로 앱 세션을 발급합니다.
- 화면 전환은 `/home`, `/files`, `/memos`, `/ai`, `/tools`, `/settings` 경로 기준으로 한 화면씩 표시합니다.
