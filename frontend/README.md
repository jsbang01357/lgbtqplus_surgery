# Qplus Surgery Frontend

정적 HTML/CSS/JavaScript 기반 수술 일정 대시보드입니다. `api_server.py`가 `frontend/index.html`과 `frontend/partials/*.html`을 조립해 제공합니다.

## 현재 화면

- `partials/login.html`: 계정 로그인 화면
- `partials/surgery.html`: 수술 일정 대시보드, 통계 카드, 필터, 등록/수정 모달, CSV import/export

## 주요 파일

- `index.html`: 공통 레이아웃, 상단바, partial include 자리
- `app.js`: 인증 상태, 라우팅, 수술 API 호출, 테이블 렌더링, 모달 이벤트
- `styles.css`: 공통 디자인 토큰과 레이아웃
- `partials/surgery.html`: 대시보드 화면과 모달 마크업
- `partials/login.html`: 로그인 폼

## 실행

```bash
.venv/bin/uvicorn api_server:app --host 127.0.0.1 --port 8080 --reload
```

내부망에서 확인할 때:

```bash
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8080 --reload
```

## 연결 API

- `GET /api/session`
- `POST /api/auth/account/login`
- `POST /api/auth/logout`
- `GET /api/surgery/cases`
- `POST /api/surgery/cases`
- `PUT /api/surgery/cases/{case_id}`
- `DELETE /api/surgery/cases/{case_id}`
- `POST /api/surgery/cases/{case_id}/cancel`
- `POST /api/surgery/cases/{case_id}/restore`
- `GET /api/surgery/summary`
- `GET /api/surgery/alerts`
- `GET /api/surgery/surgeons/summary`
- `GET /api/surgery/export.csv`
- `POST /api/surgery/import.csv`
- `GET /api/surgery/calendar/status`

## 오프라인 Calendar 표시

`GOOGLE_CALENDAR_SYNC_ENABLED=false` 또는 `OFFLINE_MODE=true`이면 Calendar 상태 API가 오프라인 모드로 응답합니다. 이때 프론트엔드는 Google 연동 버튼을 숨기고 `오프라인` 상태를 표시합니다.

## 검증

```bash
node --check frontend/app.js
```
