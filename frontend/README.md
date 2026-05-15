# Jisong Cloud Frontend

`DESIGN.md`의 Apple식 UI 언어를 반영한 새 정적 프론트엔드입니다.

현재는 기존 Streamlit 앱을 삭제하지 않고 `frontend/` 아래에 분리했습니다. 파일, 메모, AI, 도구 화면의 핵심 인터랙션을 브라우저에서 확인할 수 있고, 이후 Python API를 붙이면 기존 GCS/Gemini 로직을 그대로 연결할 수 있습니다. 운영 기준은 GCP 프로젝트이며 Cloudflare Access와 패스키 인증을 붙이는 방향입니다.

## 실행

```bash
cd frontend
python3 -m http.server 5173
```

브라우저에서 `http://127.0.0.1:5173`을 엽니다.

## 구조

- `index.html`: 앱 마크업
- `styles.css`: Apple 스타일 디자인 토큰과 반응형 레이아웃
- `app.js`: 화면 전환, 샘플 데이터, 업로드/메모/AI 데모 상태

## 연결 메모

- 실제 파일 업로드/삭제/다운로드는 기존 `app/storage.py` 로직을 API로 감싸 연결합니다.
- 실제 메모 CRUD는 기존 `app/memo.py` 로직을 API로 감싸 연결합니다.
- AI 분석은 기존 `app/ai.py`의 Gemini 비용 제한 흐름을 유지한 채 `/api/ai/analyze` 같은 단일 endpoint로 붙이는 것이 안전합니다.
- 인증은 Cloudflare Access를 외부 관문으로 두고, 앱 내부 민감 작업은 WebAuthn 패스키로 보호합니다.
