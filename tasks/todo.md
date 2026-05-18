## 현재 우선순위

### 문서/운영 기준 정리

- [x] README를 현재 Starlette API + 정적 프론트엔드 구조에 맞게 재정리
- [x] 빠진 런타임 의존성 `cryptography`를 requirements에 반영
- [x] Cloudflare Access 강제 여부와 `cloudbuild.yaml` 기본값을 운영 정책과 다시 맞추기
- [x] 로컬 검증 표준을 `.venv` / `unittest` / Node 20 기준으로 문서화하기

### 다음 기능축 후보

- [x] v6 parser-core 정밀도 개선 우선순위 확정 (Date normalization, UNIT_RE 확장, Section splitting 보강)
- [x] review UI 범위를 `v6` 중심으로 좁혀 구체화 (Metadata 편집 필드 추가, Bulk actions 반영)
- [x] GCS JSON 로그 파일의 동시성 구조 개선 및 API 서버 연동 완료

## 이번 정리 요약

- v6 브랜치 로그인 불가 원인을 점검했고, `frontend/app.js` 초기 전역 참조로 인한 부팅 크래시를 복구했다.
- 실제 운영 진입점이 `api_server.py`인 현재 구조에 맞춰 README를 다시 작성했다.
- 예전 Streamlit 중심 설명, `jisong_cloud.py`, `components/` 같은 오래된 구조 설명을 정리했다.
- 테스트 수집 실패 원인이던 누락 의존성 `cryptography`를 `requirements.txt`에 추가했다.

### 로그인 복구 (v6 branch)

- [x] 현재 브랜치와 auth/login 연결 경로 확인
- [x] 프런트엔드 부팅 크래시로 로그인 핸들러 미바인딩 원인 수정
- [x] 브라우저/테스트 기준 기본 회귀 검증

---

## 이전 작업 기록

### 보안 및 인증 레이어 강화 (마일스톤 1)

- [x] GCS 대체 로그인 비밀번호 PBKDF2-HMAC-SHA256 단방향 안전 암호화 해싱 적용
- [x] GCS 평문 비밀번호 자동 감지 및 실시간 암호화 마이그레이션(Self-Healing) 구축
- [x] 패스키 세션 검증 시 GCS JSON 매 요청 Read/Write 제거 및 로컬 인메모리 캐싱 도입 (동시성 Race Condition 차단)
- [x] 파일 업로드 확장자 화이트리스트(PDF, 이미지, TXT, CSV, Office 파일 등) 강력 도입 (악성 업로드 원천 차단)
- [x] Cloudflare Access JWT의 JWKS 퍼블릭 키 암호학적 서명(Signature) 검증 및 만료 검사 추가
- [x] 하위 호환 모킹 변경으로 단위 테스트(37개 전체) 100% 통과 검증 완료

## 요약
- GCS 평문 저장 비밀번호 취약성을 완전 제거하고, 무중단으로 기존 평문을 안전하게 해싱 변환하는 자가 치유(Self-Healing) 코드를 탑재했습니다.
- 세션 조회 시 불필요한 GCS Write를 전면 제거하고 10초 TTL 캐싱을 씌워 API 연동 속도를 기하급수적으로 단축하고 동시성 데이터를 보호했습니다.
- 파일 업로드의 보안 화이트리스트 필터를 씌우고 Cloudflare Access JWT를 암호학적으로 상호 교차 검증하도록 보강했습니다.
- 신규 보안 정책에 맞춰 유닛 테스트 모킹 대상을 갱신하고 전체 37개 테스트를 완전하게 합격시켰습니다.

---

### 프로젝트 전반 기능 파악 및 개선점 20개 도출

## 요약
- 전체 프로젝트 디렉토리를 샅샅이 스캔하여 Starlette API 서버([api_server.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/api_server.py)), 파일 관리자([storage.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/storage.py)), 메모장([memo.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/memo.py)), AI 분석([ai.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/ai.py)), 정산 계산기([settlement.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/settlement.py)), 텍스트 클리너([text_cleaner.py](file:///Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud/app/text_cleaner.py)) 등 핵심 유틸리티 및 컴포넌트들의 코드 분석을 끝마쳤습니다.
- 그 결과, 성능/비용 최적화, 보안 및 인증 강화, 메모리 및 자원 제어, 아키텍처 및 결합도 분리, 알고리즘 견고성 등의 관점에서 실질적으로 해결해야 할 **치명적인 취약점과 개선 포인트 20개**를 정밀 분석하여 상세 리포트로 도출했습니다.

---

### auth.py render_inline_html 임포트 에러 수정

- [x] `app/auth.py`의 `render_inline_html` 누락 에러 확인
- [x] `app/auth.py`에 `from app.streamlit_compat import render_inline_html` 추가
- [x] 문법 검증 및 동작 확인
- [x] 변경 요약 작성

## 요약
- `app/auth.py`에서 `render_inline_html` 함수를 참조하지만 임포트되지 않아 발생하던 에러를 수정했습니다.
- `app/streamlit_compat.py`에서 `render_inline_html`을 임포트하는 구문을 `app/auth.py` 상단에 추가했습니다.
- `.venv/bin/python3` 환경에서 `unittest`를 수행하여 37개 전체 테스트가 성공적으로 통과함을 확인했습니다.

---

### Streamlit 경고 및 모바일 UI 보정

- [x] `components.html` 사용 제거 여부 판단
- [x] 로그인/메모 자동 포커스 스크립트 유지 및 fallback 적용
- [x] idle timeout JS 주입 유지 및 fallback 적용
- [x] 모바일 사이드바 상태 박스 높이 보정
- [x] 로그인 폼 카드 여백 보정
- [x] AI 결과 PDF 준비 버튼 상태 갱신 수정
- [x] AI 분석 완료 후 결과 영역 자동스크롤 추가
- [x] Cloud Run Gemini API key를 Secret Manager 주입 방식으로 설정
- [x] Gemini 일/월 예상 비용 한도 초과 시 분석 제한
- [x] 기본 검증

## 요약
- 자동 포커스와 비활성 자동 창 닫기는 유지하되, `components.html`이 없어져도 앱 전체가 죽지 않도록 호환 렌더링 함수를 거치게 했다.
- 모바일 사이드바 상태 박스는 고정 배치를 해제하고, 로그인 폼은 하단 여백을 늘렸다.
- AI 결과 PDF는 준비 버튼을 누른 같은 실행 흐름에서 bytes를 생성하고 다운로드 버튼으로 전환되게 했다.
- Gemini 답변이 생성되면 결과 영역으로 한 번 자동스크롤되도록 했다.
- 로컬은 `secrets.toml`, Cloud Run은 Secret Manager의 `gemini-api-key`를 `GEMINI_API_KEY`로 주입하도록 배포 설정을 맞췄다.
- Gemini 예상 비용이 오늘 5,000원 또는 이번 달 15,000원 이상이면 추가 분석을 막도록 했다.

---

### 운영 안정성 개선

- [x] PPTX/DOCX/XLSX AI 분석을 텍스트 추출 방식으로 변경
- [x] Gemini 비용 로그 동시 쓰기 충돌 완화
- [x] 파일 다운로드와 AI PDF 생성의 즉시 로딩 제거
- [x] 메모 카드 HTML escaping 적용
- [x] Gemini 모델/가격/환율 설정 override 추가
- [x] 테스트와 문서 업데이트

## 요약
- PPTX/DOCX/XLSX는 Gemini에 원본 업로드하지 않고 앱에서 OOXML 텍스트를 추출해 프롬프트에 포함하도록 변경했다.
- Gemini 사용량 로그는 GCS generation 조건부 업로드와 재시도로 동시 쓰기 충돌을 줄였다.
- 파일 다운로드와 AI PDF는 준비 버튼을 누른 뒤에만 bytes를 생성하도록 바꿨다.
- 메모 카드의 제목/시간/미리보기 HTML escaping을 적용했다.
- Gemini 모델, 단가, USD/KRW 환산값은 환경변수나 `st.secrets["gemini"]`로 override 가능하게 했다.

---

### 인증 경로 테스트 및 문서 정리

- [x] 계정 로그인 API 성공/실패 테스트 추가
- [x] 비밀번호 변경 API 성공/실패 테스트 추가
- [x] `JISONG_ACCOUNT_PASSWORD` 관련 문서와 배포 설정 정리

## 요약
- 계정 로그인과 비밀번호 변경의 성공/실패 경로를 직접 검증하는 테스트를 추가했다.
- 인증 관련 기존 테스트는 현재 GCS 기반 세션 저장 방식에 맞게 정리했다.
- 문서와 Cloud Build 설정에서 `JISONG_ACCOUNT_PASSWORD` 하드코딩을 제거하고, 계정 비밀번호는 GCS의 `auth/account_password.txt`로 설명을 맞췄다.

---

### UI 점검 및 미구현 기능 제거

- [x] Gemini 설정 저장 버튼의 런타임 에러 수정
- [x] `오늘 뭐 먹지?` 기능 제거
- [x] 관련 문서와 도구 목록 정리

## 요약
- Gemini 요금 설정 저장 후 존재하지 않는 갱신 함수를 호출하던 부분을 실제 갱신 경로로 바꿨다.
- `오늘 뭐 먹지?`는 HTML/Streamlit 양쪽에서 노출되던 흔적을 제거했다.
- README의 기능 목록과 프로젝트 구조도 현재 코드 기준으로 맞췄다.

---

### Mac mini 병행 서버 Phase 2 구성

- [x] 기존 Cloud Run 배포와 로컬 실행 경로 확인
- [x] Mac mini용 Docker Compose와 환경 변수 샘플 추가
- [x] Cloudflare Tunnel 및 Access 운영 문서 추가
- [x] AI 화면에서 Ollama 로컬 모델 선택 경로 추가
- [x] 기본 검증 실행

## 요약
- Cloud Run용 `Dockerfile`은 유지하고, Mac mini 병행 운영 전용 `docker-compose.local.yml`과 `.env.local.example`을 추가했다.
- `mac.jisong.dev`용 Cloudflare Tunnel, Access 정책, 내부 관리자 비밀번호 역할을 `docs/mac-mini-phase2.md`에 정리했다.
- AI 화면에서 Gemini, Ollama, auto fallback 모드를 선택할 수 있게 하고, Ollama는 텍스트 기반 자료를 `host.docker.internal:11434` 또는 `ai.mac.jisong.dev`로 전달하도록 했다.
- Ollama 실제 설치 모델명 `gemma4:e4b`, `qwen3.5:9b`를 앱 옵션과 환경 샘플에 반영했다.
- 문법 검증과 `unittest discover` 기준 기본 테스트를 통과했다.
- Docker 설치 후 `docker compose -f docker-compose.local.yml config`, `docker compose -f docker-compose.local.yml build jisong-cloud`, 빌드 이미지 내부 `py_compile`까지 통과했다.

---

### Mac mini 로컬 저장소 mirror

- [x] GCS 직접 호출 구조 확인
- [x] 로컬 파일 기반 bucket adapter 추가
- [x] Mac mini compose에 로컬 저장소 volume과 `local_mirror` 환경변수 추가
- [x] 로컬 backend 다운로드 동작을 Streamlit 다운로드 버튼으로 분기
- [x] 로컬 저장소 동작 테스트 추가
- [x] 로컬-only 파일을 GCS로 다시 올리는 reconcile 경로 추가
- [x] 도구모음에 저장소 상태와 수동 동기화 추가
- [x] Docker/테스트 검증 실행

## 요약
- `STORAGE_BACKEND=local_mirror`를 추가해 Mac mini에서는 로컬 디스크를 우선 읽고 쓰며 GCS에 mirror할 수 있게 했다.
- 로컬 저장소는 compose에서 `/Users/jsbang/jisong-data/storage`를 컨테이너 `/data/jisong-cloud`에 mount한다.
- 로컬 backend는 signed URL 대신 Streamlit 다운로드 버튼으로 파일을 내려받는다.
- 목록 조회와 수동 동기화 시 GCS pull 이후 로컬-only 파일을 GCS로 push하도록 보강했다.
- 도구모음에 `저장소 상태`를 추가해 backend, 로컬/GCS 파일 수, 로컬 용량, 수동 동기화를 확인할 수 있게 했다.
- 로컬 mirror 테스트를 포함해 `unittest discover` 17개, compose config, Docker build, 로컬-only 컨테이너 기동과 HTTP 200 확인까지 통과했다.

---

### Mac mini 로컬 컨테이너 기동

- [x] `.streamlit/secrets.toml` 기준으로 `.env.local` 생성
- [x] Docker용 GCS service account JSON 생성
- [x] 로컬 저장소 bind mount 경로 생성
- [x] `jisong-cloud` 컨테이너 빌드 및 기동
- [x] `127.0.0.1:8501` HTTP 응답 확인
- [x] 컨테이너 내부 `local_mirror` backend 상태 확인

## 요약
- `.env.local`과 `.streamlit/gcp-service-account.json`을 생성했다.
- `jisong-cloud-local` 컨테이너가 `127.0.0.1:8501 -> 8080`으로 실행 중이다.
- 컨테이너 내부 저장소 backend는 `local_mirror`이며 GCS mirror/pull이 켜져 있다.
- Cloudflare Tunnel token은 아직 없어 `cloudflared`는 실행하지 않고 앱 컨테이너만 먼저 올렸다.

---

### Mac mini tunnel 및 로그 pull 보정

- [x] `mac.jisong.dev` static asset 실패 원인 확인
- [x] Cloudflare dashboard의 `localhost:8501` origin이 컨테이너 내부 localhost를 보던 문제 수정
- [x] GCS `logs/access_log.json`, `logs/gemini_usage.json` 단일 파일 pull 경로 수정
- [x] 테스트와 Docker 재기동 검증

## 요약
- `cloudflared`가 앱 컨테이너와 같은 network namespace에서 실행되도록 바꾸고, Streamlit local compose port를 8501로 맞췄다.
- `mac.jisong.dev/_stcore/health`와 문제가 났던 `DataFrame.DUkanX9_.css`가 200으로 응답하는 것을 확인했다.
- `blob.exists()`에서 GCS remote blob을 확인해 없던 단일 로그 파일도 로컬로 pull되도록 수정했다.
- `logs/access_log.json`, `logs/gemini_usage.json`가 컨테이너 내부에서 `exists() == True`로 확인됐다.

---

### Mac mini 보안 및 자동 기동 점검

- [x] 외부 도메인 응답과 Cloudflare Access 적용 여부 확인
- [x] `.env.local` 및 Docker용 service account JSON 권한 축소
- [x] Mac mini 로컬 compose에서 전체 앱 관리자 인증 옵션 추가
- [x] LaunchAgent 자동 기동 스크립트와 plist 추가
- [x] LaunchAgent 설치 및 1회 실행 확인
- [x] 기본 문법 및 테스트 검증

## 요약
- `mac.jisong.dev`는 현재 curl에서 200을 반환하므로 Cloudflare Access가 앞단에서 강제되고 있지는 않은 상태로 판단했다.
- local compose에는 `REQUIRE_AUTH_ALL=true`를 추가해 Cloudflare Access가 없어도 도구모음까지 앱 내부 관리자 로그인을 거치게 했다.
- `.env.local`과 `.streamlit/gcp-service-account.json` 권한을 `600`으로 낮췄다.
- `scripts/start-local-server.sh`와 `launchd/com.jisong.cloud.local.plist`를 추가하고 `~/Library/LaunchAgents/com.jisong.cloud.local.plist`에 설치했다.
- LaunchAgent는 `last exit code = 0`으로 실행됐고 compose 컨테이너 재생성을 수행했다.

---

### 프로젝트 전반 개선점 점검

- [x] 현재 작업트리와 주요 파일 구조 확인
- [x] AI, 저장소, 메모, 도구, 배포 설정 점검
- [x] 테스트/문법 검증 실행
- [x] 우선순위별 개선점 요약

## 요약
- 현재 작업트리는 `app/ai.py`와 `tasks/todo.md` 변경만 남아 있다.
- 기본 테스트와 문법 검증은 통과했다.
- 우선 개선점은 GCS JSON 로그 동시 쓰기, ZIP 메모리 사용, HTML escaping, 비용 설정값 분리, 테스트 커버리지 확장이다.

---

- [x] VS Code `launch.json`에 API 서버(Uvicorn) 실행 설정 추가

# 📝 Todo

Use this file to write short checklists for non-trivial work.
Mark items as complete as you go.

---

- [x] Read the repository structure and main entrypoints
- [x] Inspect core modules for storage, memos, tools, auth, and logging
- [x] Review deployment/configuration files and supporting assets
- [x] Summarize architecture, behavior, risks, and improvement opportunities

## Summary
- Reviewed the full codebase and mapped how the Streamlit app routes into GCS-backed file, memo, tool, auth, and access-log features.
- Identified a few architecture mismatches between README claims and current implementation, plus several maintainability and security risks to watch.

- [x] Re-read the current README against the implementation
- [x] Rewrite README to match the current project behavior only
- [x] Verify the updated README is consistent with the repository structure
- [x] Inspect dependency and ignore-file consistency
- [x] Update requirements.txt to match runtime imports
- [x] Clean up .gitignore for the current repo workflow
- [x] Polish README wording after dependency/ignore cleanup

## Summary
- Added the missing runtime dependency used by the access-log admin table.
- Cleaned `.gitignore` to match current local-development artifacts while keeping repo-managed task files and instructions trackable.
- Updated README so installation and repo-management notes align with the current dependency and local-config setup.

---

## 텍스트 클리너 마크다운 변환 개선

- [x] 기존 텍스트 클리너 구조와 옵션 흐름 확인
- [x] 마크다운을 읽기 좋은 plain text / Word용 텍스트로 변환하는 함수 추가
- [x] 출력 형식 선택 UI와 상세 옵션 정리
- [x] 샘플 입력으로 변환 결과 검증
- [x] 변경 요약 작성

## 요약
- 텍스트 클리너에 출력 형식 선택을 추가해 기본 정리, Markdown → Plain Text, Markdown → Word용 텍스트를 나눴다.
- 마크다운 제목, 인라인 서식, 링크, 이미지, 인용문, 목록, 코드블록을 복사하기 좋은 텍스트로 변환하도록 분리했다.
- 코드블록 placeholder가 마크다운 정규식에 다시 변형되지 않도록 검증했다.

---

## Jisong Cloud UI 개선

---

## JisongCloud v6 아키텍처 재설계

- [x] 기존 v5 구조와 최근 설계/운영 맥락 확인
- [x] v6 핵심 철학과 클라우드/로컬 역할 재정의
- [x] EMR 정규화 파이프라인과 modality별 출력 구조 설계
- [x] 메타데이터, chunk parsing, local sync 전략 설계
- [x] 프론트엔드 surface와 abstraction/migration 계획 정리
- [x] 위험요소와 단계별 전환 전략 정리

## 요약
- v6는 AI 중심 웹앱이 아니라 EMR ingestion과 normalization을 담당하는 lightweight cloud bridge로 재정의했다.
- canonical brain은 로컬 Mac workspace로 두고, cloud는 업로드, 정규화, 메타데이터 부착, sync trigger까지만 맡는 구조로 정리했다.
- 출력 형식은 modality별 `csv`와 `md`를 기본으로 하고, patient workspace 디렉터리와 metadata/manifest 레이어를 함께 설계했다.

### 다음 구현 계획

- [x] clean_text 레포의 TSX 파싱 로직을 inventory하고 순수 파서 코어와 UI 의존부를 분리한다.
- [x] modality 공통 schema와 document manifest schema를 TS 타입으로 먼저 고정한다.
- [x] `labs`, `medications`, `imaging`, `pathology`, `notes`용 parser interface를 정의한다.
- [x] chunk splitter와 classifier를 heuristic-first 방식으로 구현한다.
- [x] CSV/Markdown artifact writer와 frontmatter metadata writer를 구현한다.
- [x] local workspace sync manifest 포맷과 상대 경로 규칙을 TS로 고정한다.
- [x] GCS staging publish/pull contract를 구현한다.
- [x] v5 Starlette API에 `/api/v6/health`, `/api/v6/parse` 경로를 병행 추가한다.
- [x] mixed EMR blob의 note/lab/imaging 분리 heuristic과 회귀 테스트를 추가한다.
- [x] lightweight intake/review frontend는 parser 결과 검수용 surface만 남기고 범용 AI UI는 축소한다.

## 진행 메모
- `Clean_Text`의 `labParser.ts`, `textCleaner.ts`를 기준으로 `v6/parser-core` 독립 TS 패키지를 추가했다.
- `app/v6_bridge.py`와 `api_server.py`에 Node CLI 기반 bridge를 추가했고, Dockerfile도 parser-core build를 수행하도록 맞췄다.
- chunk splitter는 `[Chemistry]`, `CT Abdomen`, `Findings/Impression` 같은 내부 섹션을 과분리하지 않도록 조정했고, mixed blob regression test를 추가했다.
- 아직 남은 큰 작업은 parser precision 보강, GCS/local sync publish contract, review UI다.

- [x] 현재 전역 레이아웃과 도구모음 UI 구조 점검
- [x] 전역 스타일과 사이드바 톤 정리
- [x] 도구모음 선택 UI와 화면 헤더 재구성
- [x] 기본 문법 및 동작 검증
- [x] 변경 요약 작성

## 요약
- 전역 CSS를 추가해 앱 배경, 카드 표면, 입력창, 메트릭, 사이드바 버튼의 톤을 통일했다.
- 사이드바를 앱 소개와 상태 요약이 함께 보이는 작업 허브 형태로 정리했다.
- 도구모음을 selectbox 대신 상단 선택 패널과 화면별 헤더 구조로 바꿔 어떤 도구를 쓰는지 바로 보이도록 개선했다.

---

## Jisong Cloud 남색 테마 확장

- [x] 남색 중심 전역 테마로 색상 재조정
- [x] 웹하드, 메모장, 로그인 화면 헤더와 섹션 정리
- [x] 남은 화면들 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 전역 포인트 컬러를 초록에서 남색 계열로 바꾸고 배경, 사이드바, 선택 버튼의 톤을 다시 맞췄다.
- 웹하드, 메모장, 로그인 화면에도 공통 히어로와 섹션 카드 패턴을 적용해 앱 전체 흐름을 통일했다.
- 문법 검증으로 수정된 화면 모듈들이 모두 정상 파싱되는지 확인했다.

---

## Apple 스타일 프론트엔드 전환

- [x] `DESIGN.md`와 기존 Streamlit 진입점 확인
- [x] 새 프론트엔드 구조와 Apple식 디자인 토큰 구현
- [x] 웹하드/메모/AI/도구 주요 화면을 정적 앱으로 구성
- [x] 실행 문서와 기본 검증 추가
- [x] 변경 요약 작성

## 요약
- `frontend/` 아래에 Streamlit과 분리된 정적 프론트엔드 미리보기를 추가했다.
- `DESIGN.md` 기준의 블랙 global nav, frosted sub-nav, light/dark full-bleed tile, 단일 파란 CTA, SF Pro 계열 typography 토큰을 적용했다.
- 웹하드, 메모장, AI, 도구모음의 주요 화면과 버튼/폼 상호작용을 브라우저 로컬 상태로 구현했다.
- 기존 Python/GCS/Gemini 로직은 유지하고, 다음 단계에서 API로 연결할 수 있도록 실행 문서를 남겼다.
- `node --check frontend/app.js`, `python3 -m py_compile ...`, Safari 렌더링 확인을 완료했다.

---

## GCP 기준 운영 전환

- [x] 로컬 Docker 호스팅 파일 제거
- [x] Ollama/local LLM provider 제거
- [x] local mirror 저장소 adapter 제거
- [x] README와 프론트 문구를 GCP/Cloudflare Access/패스키 방향으로 수정
- [x] 보안 전환 계획 문서 추가

## 요약
- `docker-compose.local.yml`, Mac mini 운영 문서, launchd 로컬 기동 파일, `.env.local.example`을 제거했다.
- AI 분석은 Gemini-only 흐름으로 정리하고 Ollama/auto fallback 선택 UI와 호출 코드를 제거했다.
- 저장소는 GCS 직접 사용 기준으로 정리하고 local mirror adapter와 관련 테스트를 제거했다.
- `docs/gcp-security-plan.md`에 Cloudflare Access와 패스키 인증 전환 순서를 남겼다.

---

## API 서버 및 패스키 인증 1차 구현

- [x] Starlette 기반 `api_server.py` 추가
- [x] Cloudflare Access 헤더 검증 유틸 추가
- [x] WebAuthn 패스키 등록/로그인 challenge 및 서명 검증 추가
- [x] 새 프론트엔드에 패스키 등록/로그인 버튼 연결
- [x] Cloud Run 진입점을 `uvicorn api_server:app`으로 변경
- [x] 기본 테스트와 문법 검증 실행
- [x] `jsbang01357@gmail.com`만 기본 허용 계정으로 제한
- [x] 패스키 미지원 환경에서는 Cloudflare Access Google 인증으로 fallback 허용

## 요약
- 새 API 서버가 `frontend/` 정적 파일과 `/api/*` endpoint를 함께 제공하도록 했다.
- 민감 API는 기본적으로 `jsbang01357@gmail.com` Cloudflare Access 통과를 확인하고, passkey session 또는 Google 인증 fallback 중 하나를 요구한다.
- 패스키 credential과 session은 GCS의 `auth/passkeys.json`에 저장한다.
- Docker/Cloud Build 환경변수는 `cloud.jisong.dev` 기준 passkey RP 설정을 포함하도록 바꿨다.

---

## Jisong Cloud 리스트 UX 개선

- [x] 파일 목록 가독성 개선
- [x] 메모 목록 가독성 개선
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 파일함에 검색, 파일 수/표시 수/전체 용량 요약, 파일별 수정 시각과 용량 메타 정보를 추가했다.
- 메모장에 검색, 메모 수 요약, 펼치기 전 미리보기와 수정 시각 표시를 추가해 훑어보기 쉽게 만들었다.
- 문법 검증으로 리스트 UX 개선이 기존 모듈과 충돌하지 않는지 확인했다.

---

## Jisong Cloud 액션 버튼 압축

- [x] 파일 목록 액션 버튼 간결화
- [x] 메모 목록 액션 버튼 간결화
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 파일 목록에서 메타 정보와 액션 버튼을 한 줄 레이아웃으로 묶고 버튼 라벨을 짧게 줄였다.
- 메모 상세 액션의 저장, 복사, 다운로드, 삭제 버튼 라벨을 압축해 화면 밀도를 높였다.
- 문법 검증과 diff 검사로 압축된 버튼 구성이 기존 동작을 깨지 않는지 확인했다.

---

## Jisong Cloud 메모 카드화

- [x] 메모 목록을 카드형 요약 구조로 재배치
- [x] 카드 내부 액션과 수정 영역 정리
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 메모 목록을 제목과 미리보기가 먼저 보이는 카드형 요약 구조로 바꾸고, 수정 영역은 별도 펼침 영역으로 분리했다.
- 카드에서 읽기와 선택을 먼저 하고, 필요한 경우에만 편집 액션을 여는 흐름으로 정리했다.
- 문법 검증과 diff 검사로 카드형 메모 목록이 기존 저장/복사/다운로드/삭제 흐름과 충돌하지 않는지 확인했다.

---

## Jisong Cloud 파일 카드화

- [x] 파일 목록을 카드형 요약 구조로 재배치
- [x] 카드 내부 액션과 메타 정보 정리
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 파일 목록을 제목과 메타 정보가 먼저 보이는 카드형 구조로 바꾸고, 다운로드와 삭제는 카드 아래 짧은 액션으로 분리했다.
- 메모 카드와 비슷한 읽기 흐름으로 맞춰서 파일함도 목록 스캔과 선택이 더 자연스럽게 이어지도록 정리했다.
- 문법 검증과 diff 검사로 카드형 파일 목록이 기존 다운로드/삭제 흐름과 충돌하지 않는지 확인했다.

---

## Jisong Cloud 테마 보정 및 파일 아이콘

- [x] 남색 전역 테마와 사이드바 색상 보정
- [x] 웹하드 파일 확장자별 아이콘 추가
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- Streamlit 테마 설정과 전역 CSS를 함께 보정해 기본 포인트 컬러가 남색으로 맞춰지도록 정리했다.
- 사이드바 전체 배경을 남색으로 고정하고, `Jisong Cloud` 헤더와 보조 문구가 밝은 색으로 읽히도록 보강했다.
- 웹하드 파일 카드에 PDF, Word, PowerPoint, Excel, TXT, 이미지, 압축파일 등 확장자별 아이콘을 붙여 목록 식별성을 높였다.

---

## Jisong Cloud 대비 및 카드 정리

- [x] 선택된 사이드바 버튼 대비 보정
- [x] 반복 섹션 카드를 더 단순한 구획으로 정리
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 선택된 사이드바 버튼 내부 텍스트 색을 강하게 고정해 밝은 배경 위에서도 겹치지 않고 읽히도록 보정했다.
- 반복 설명 영역을 카드 대신 얇은 섹션 구획으로 바꿔서 실제 데이터 카드가 더 또렷하게 보이도록 정리했다.
- 문법 검증과 diff 검사로 전역 스타일 조정과 화면 구조 변경이 기존 동작과 충돌하지 않는지 확인했다.

---

## Jisong Cloud 로컬 파일 아이콘 자산화

- [x] 로컬 SVG 파일 아이콘 자산 추가
- [x] 웹하드 카드에 로컬 아이콘 렌더링 연결
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 웹하드 파일 카드에서 쓰는 파일 타입 아이콘을 `assets/icons/filetypes` 아래 로컬 SVG 자산으로 교체했다.
- PDF, Word, PowerPoint, Excel, 텍스트, 마크다운, 이미지, 압축파일, 미디어, 기본 파일 타입을 분리해 카드에서 더 일관되게 보이도록 정리했다.
- 파일 카드 레이아웃을 아이콘 중심으로 다시 묶어서 확장자 배지, 파일명, 수정 시각, 용량이 한 덩어리로 읽히게 맞췄다.

---

## Jisong Cloud 사이드바 및 경고 영역 보정

- [x] Danger Zone 강조 색상 보정
- [x] 사이드바 상태 박스 시각 톤 정리
- [x] 헤더와 푸터 타이포 조정
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 웹하드의 Danger Zone 섹션에 빨간 계열 강조 스타일을 추가해 경고 영역이 바로 구분되도록 정리했다.
- 사이드바의 현재 시간과 마지막 접속 박스를 메뉴 버튼과 비슷한 남색 반투명 버튼 톤으로 맞췄다.
- `Jisong Cloud` 헤더 크기를 키우고, 푸터 메타는 줄바꿈과 옅은 색으로 조정해 읽기 흐름을 가볍게 만들었다.

---

## Jisong Cloud 섹션 간격 보정

- [x] 화면별 섹션 구획 구조 확인
- [x] 섹션 여백 스타일 보강
- [x] 웹하드/메모장/도구모음에 구획 클래스 반영
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 전역 CSS에 `section-block--spacious` 규칙을 추가해 다음 섹션이 시작될 때 여백과 얇은 구분선이 한 번 더 들어가도록 정리했다.
- 웹하드, 메모장, 도구모음에서 `Library`, `Batch`, `Danger Zone`, 도구 헤더 같은 다음 단계 섹션에 여백 클래스를 적용했다.
- 색을 더 늘리지 않고도 섹션 전환이 보이도록 간격 중심으로 정리해 카드와 폼이 한 덩어리로 붙어 보이는 느낌을 줄였다.

---

## Jisong Cloud 사이드바 텍스트 압축

- [x] 직전 접속 표시 포맷 축약
- [x] 사이드바 헤더 정렬과 크기 조정
- [x] 푸터 대비 재조정
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 사이드바 상태 라벨을 `현재 시간`, `직전 접속`으로 정리하고, 직전 접속 값은 `월/일 시:분` 형식으로 축약해 줄바꿈이 덜 생기도록 바꿨다.
- `Jisong Cloud` 제목을 좌측 정렬 상태에서 더 크게 키워 사이드바의 메인 타이틀 역할이 더 분명하게 보이도록 조정했다.
- 푸터 메타 텍스트는 기존보다 조금 더 어둡게 낮춰서 제목과 상태 정보보다 뒤로 물러나게 정리했다.

---

## Jisong Cloud 도구 전환 및 Danger 버튼 보정

- [x] 도구 전환 반응성 개선
- [x] Danger 버튼 전용 스타일 적용
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
## 현재 변경 파악

- [x] 변경 파일과 의도 확인
- [x] 타입 검사 설정 및 무시 주석 영향 확인
- [x] 기존 테스트/기본 검증 실행
- [x] 변경 요약 작성

## 요약
- 현재 변경은 기능 추가보다 `pyrefly` 타입 검사 도입 과정의 무시 주석 추가가 중심이다.
- 초기에 보였던 `pyrefly.toml`은 최종 확인 시 파일 시스템과 git 상태에서 사라졌고, 현재 로컬 Python 환경에는 `pyrefly` 모듈이 설치되어 있지 않다.
- `python3 -m unittest discover -s tests`와 `python3 -m py_compile jisong_cloud.py app/*.py tests/*.py`는 통과했다.

---

## AI 비용 원화 표시 및 도구 순서 조정

- [x] AI 예상 비용 표시를 KRW 반올림 기준으로 변경
- [x] 사이드바 상태 박스에 이번 달 AI 비용 추가
- [x] 분석 완료 직후 비용 표시가 갱신되도록 캐시/리렌더 처리
- [x] Gemini usage JSON 로그 누적 정책 확인
- [x] 도구모음 순서를 텍스트 클리너, MD to PDF, 글자수, 정산, 메뉴, 접속기록 순서로 변경

## 요약
- Gemini 예상 비용을 앱 내 USD/KRW 환산값으로 원화 표시하고 1원 미만은 반올림하도록 바꿨다.
- 이번 달 AI 비용을 사이드바 상태 박스의 직전 접속 아래에 표시하도록 추가했다.
- 분석 완료 후 usage 로그 캐시를 비우고 rerun해서 결과 화면과 비용 표시가 바로 갱신되게 했다.
- `logs/gemini_usage.json`은 최근 1,000건만 유지하므로 Cloud Run에서도 무한 누적되지 않는다.
- 도구모음 버튼 순서를 요청한 순서로 재배치했다.

---

## 정산 계산기 입력 방식 개편

- [x] 사람 입력을 상단 한 줄 입력으로 변경
- [x] 지출 입력 열을 돈낸사람/비용/n빵할사람/항목 순서로 변경
- [x] n빵할사람/항목 생략 처리와 검증 메시지 정리
- [x] 결과 표 제거 및 문장형 출력으로 변경
- [x] 테스트와 README 업데이트

## 요약
- 정산 계산기 입력을 사람 한 줄 입력과 `돈낸사람`, `비용`, `n빵할사람`, `항목` 4열 지출 입력으로 바꿨다.
- `돈낸사람`과 `비용`은 필수로 검증하고, `n빵할사람`이 비어 있으면 전체 n빵으로 계산한다.
- 결과 dataframe 표를 제거하고 사람별 잔액과 최소 송금 목록을 문장형으로 표시하도록 변경했다.
- 새 입력 키 기준 테스트와 선택 항목 생략 테스트를 추가했다.

---

## AI 예상 비용 표시

- [x] Gemini 3 Flash Preview 가격 기준 확인
- [x] Gemini usage metadata를 비용 로그로 저장
- [x] 오늘/이번 달 예상 누적 비용을 AI 상단에 표시
- [x] README와 기본 검증 업데이트

## 요약
- Gemini 3 Flash Preview 유료 Standard 단가 기준으로 input $0.50/1M tokens, output $3.00/1M tokens를 적용했다.
- Gemini 응답의 usage metadata에서 입력/출력 토큰을 추출해 `logs/gemini_usage.json`에 저장하도록 했다.
- AI 화면 상단에 오늘/이번 달 예상 Gemini 비용과 현재 모델명을 표시하도록 했다.
- 비용 로그에는 환자 자료나 프롬프트 본문을 저장하지 않고 토큰 수와 추정 비용만 남긴다.

---

## AI 프리셋 토글 및 결과 내보내기

- [x] 프리셋 버튼을 토글 상태로 전환
- [x] 프리셋 재클릭 시 해당 프롬프트 제거
- [x] AI 결과 하단에 복사/MD/PDF 내보내기 추가
- [x] 기본 검증 후 요약 작성

## 요약
- AI 프리셋 버튼은 선택 시 primary 색상으로 바뀌고, 다시 누르면 해당 프롬프트를 질문 입력칸에서 제거하도록 변경했다.
- AI 결과 하단에 복사, Markdown 다운로드, PDF 다운로드 영역을 추가했다.
- PDF 다운로드는 기존 MD to PDF 변환 함수를 재사용하며, 변환 실패 시 안내 메시지를 보여준다.

---

## AI Office 파일 접근 확장

- [x] Gemini 지원 파일 형식 확인
- [x] AI 분석 대상 확장자를 Word/Excel/PPT까지 확대
- [x] README와 기본 검증 업데이트
- [x] 변경 요약 작성

## 요약
- Gemini Files API/File Search 공식 문서의 지원 MIME 목록을 확인하고 Office 파일 확장자를 AI 분석 대상에 추가했다.
- AI 파일 필터에 `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`를 포함했다.
- README와 AI 화면 안내 문구를 Word/Excel/PPT까지 포함하도록 갱신했다.

---

## Gemini 3 Flash 모델 지정

- [x] 현재 Gemini 모델 문자열 확인
- [x] AI 분석 모델을 Gemini 3 Flash Preview로 변경
- [x] 기본 검증 후 요약 작성

## 요약
- 기존 AI 분석 모델은 `gemini-2.5-flash`였다.
- 모델명을 `GEMINI_MODEL = "gemini-3-flash-preview"` 상수로 분리하고 Gemini 호출에서 사용하도록 변경했다.
- README에 AI 메뉴가 Gemini 3 Flash Preview를 사용한다고 반영했다.

---

## Jisong Cloud AI 프롬프트 프리셋

- [x] 자주 쓰는 임상 발표/질문 프리셋 정의
- [x] AI 질문 입력칸에 프리셋 버튼 append 동작 추가
- [x] README와 기본 검증 업데이트
- [x] 변경 요약 작성

## 요약
- AI 화면에 SOAP 1분 발표, 예상 Q&A, 교수님께 질문, 문제목록/계획 프리셋 버튼을 추가했다.
- 프리셋 버튼을 누르면 기존 질문 입력을 지우지 않고 아래에 프롬프트를 덧붙이도록 했다.
- README에 AI 프리셋 기능을 반영하고 기본 테스트와 문법 검증을 통과했다.

---

## MD to PDF 로컬 WeasyPrint 오류 안내

- [x] WeasyPrint 로컬 네이티브 라이브러리 오류 원인 확인
- [x] 앱 오류 메시지를 설치 안내 중심으로 개선
- [x] README에 macOS 로컬 설치 안내 추가
- [x] 기본 검증 후 요약 작성

## 요약
- 로컬 macOS에서 `libgobject-2.0-0` 등 WeasyPrint 네이티브 라이브러리가 없어 PDF 생성이 실패하는 상황을 확인했다.
- `app/md_pdf.py`에서 `OSError`를 잡아 Homebrew 설치 명령을 포함한 안내 메시지를 보여주도록 개선했다.
- README 실행 방법에 macOS 로컬용 `brew install glib pango gdk-pixbuf libffi` 안내를 추가했다.

---

## Jisong Cloud AI 메모 입력 확장

- [x] AI 사이드바 아이콘 깨짐 수정
- [x] AI 분석 입력에 메모장 텍스트 선택 추가
- [x] 문서와 기본 검증 업데이트
- [x] 변경 요약 작성

## 요약
- AI 사이드바 버튼에서 깨지는 emoji 아이콘을 제거하고 텍스트 라벨로 정리했다.
- AI 분석 화면에서 메모장 텍스트를 최대 5개 선택해 웹하드 파일/추가 텍스트와 함께 분석할 수 있게 했다.
- 메모는 이미 GCS `memos/*.txt`로 저장되므로 저장 방식을 바꾸지 않고 기존 텍스트 본문을 프롬프트 입력으로 재사용했다.

---

- 도구모음 선택 버튼은 상태 변경 직후 `_select_tool()`에서 즉시 `st.rerun()` 하도록 바꿔서 화면 전환 체감이 더 빠르게 반영되도록 정리했다.
- 웹하드, 메모장, 접속 기록 관리의 전체 삭제 버튼에 전용 key를 부여하고, 전역 CSS에서 해당 key만 빨간 강조 버튼으로 스타일링했다.
- 문법 검증과 diff 검사로 도구 전환 로직과 Danger 버튼 스타일이 기존 동작을 깨지 않는지 확인했다.

---

## Jisong Cloud 컴포넌트 마감 다듬기

- [x] 실제 화면 기준으로 겹침/정렬 문제 확인
- [x] 도구모음, 로그인, 텍스트 클리너 밀도 조정
- [x] 전역 타이포와 버튼 줄바꿈 보정
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 실제 도구모음 화면을 기준으로 좁은 폭에서 먼저 무너질 수 있는 4열 버튼, 4열 메트릭, 가로 라디오 같은 요소를 확인했다.
- 도구모음 선택 버튼은 2열 배치로 낮추고, 글자수 카운터 메트릭은 2x2 구조로 바꿔 좁은 화면에서도 문구가 덜 겹치게 정리했다.
- 로그인 폼은 가운데 좁은 폭으로 모으고, 전역 버튼 줄바꿈과 폼 카드 스타일을 보강해 전체 컴포넌트 밀도를 더 안정적으로 맞췄다.

---

## Jisong Cloud 메모 포커스 보정

- [x] 메모 작성 포커스 스크립트 원인 확인
- [x] 제목 자동 포커스 동작 완화
- [x] 기본 문법 검증
- [x] 변경 요약 작성

## 요약
- 메모 작성 영역에서 제목 입력 후 내용칸으로 갈 때 두 번 클릭이 필요하던 원인은 제목 자동 포커스 스크립트가 렌더링 뒤 반복적으로 포커스를 되돌리기 때문이었다.
- 자동 포커스는 초기 진입 편의를 위해 유지하되, 다른 입력칸에 이미 포커스가 있으면 건드리지 않고 제목칸이 비어 있을 때만 한 번 실행되도록 완화했다.
- 문법 검증과 diff 검사로 메모 작성 UX 보정이 기존 저장 흐름과 충돌하지 않는지 확인했다.

---

## Jisong Cloud 복사 버튼 스타일 통일

- [x] 커스텀 복사 버튼 프론트엔드 구조 확인
- [x] 앱 전역 버튼 톤과 맞게 CSS 보정
- [x] 기본 문법 및 diff 검증
- [x] 변경 요약 작성

## 요약
- 복사 버튼이 삭제/다운로드 버튼과 다르게 보이던 이유는 `custom_copy_btn`이 별도 프론트엔드 컴포넌트로 렌더되어 전역 `st.button` CSS를 직접 받지 않기 때문이었다.
- 커스텀 버튼 CSS를 앱 전역 버튼 톤에 맞춰 배경, 테두리, 높이, 라운드, hover/active 색상을 남색 계열로 다시 정리했다.
- diff 검사와 문법 검증으로 복사 버튼 스타일 통일 작업이 기존 메모/텍스트 클리너 동작을 깨지 않는지 확인했다.

---

## Jisong Cloud 전체 삭제 이중 확인

- [x] 파일/메모 전체 삭제 흐름 점검
- [x] 두 번 클릭 확인 로직 적용
- [x] 기본 문법 및 diff 검증
- [x] 변경 요약 작성

## 요약
- 웹하드와 메모장의 전체 삭제 버튼은 첫 클릭에서 바로 실행되지 않고, 확인 상태를 켠 뒤 두 번째 클릭에서만 실제 삭제가 일어나도록 바꿨다.
- 확인 상태가 켜지면 경고 메시지와 버튼 라벨이 함께 바뀌어 지금이 삭제 직전 단계라는 점이 분명하게 보이도록 정리했다.
- 문법 검증과 diff 검사로 이중 확인 로직이 기존 전체 삭제 흐름과 충돌하지 않는지 확인했다.

---

## Jisong Cloud AI 및 도구 확장

- [x] Add idle timeout behavior and AI sidebar route
- [x] Add Gemini file/text analysis screen
- [x] Add Markdown to PDF converter tool
- [x] Add itemized settlement calculator tool
- [x] Move memo copy/download/delete actions outside the edit expander
- [x] Update dependencies and deployment/runtime notes
- [x] Verify syntax and settlement scenarios

## Summary
- Added an authenticated AI sidebar menu that analyzes selected GCS files and typed text with Gemini, then saves results as memos.
- Added Markdown to PDF and itemized settlement tools under the tools menu.
- Added a 10-minute idle close attempt with a browser-policy fallback screen.
- Moved memo copy/download/delete actions outside the edit expander.
- Updated runtime dependencies, Docker system packages, README notes, and settlement unit tests.

---

## 푸시 전 변경 정리

- [x] 현재 변경 파일과 누락 구현 확인
- [x] 기존 `tasks/todo.md`, `tasks/lessons.md` 기록 복구
- [x] AI 멀티턴/후처리/내보내기 구현 정리
- [x] 로그인 실패 제한과 파일 다운로드 UX 점검
- [x] 테스트와 문법 검증 실행
- [x] 최종 변경 요약 작성

## 요약
- 기존 작업 기록을 보존하도록 `tasks/todo.md`, `tasks/lessons.md`를 복구하고 이번 정리 내역만 추가했다.
- AI 멀티턴 프롬프트, 결과 후처리, 대화 PDF 내보내기 누락 구현을 보완하고 helper 테스트를 추가했다.
- 로그인 실패 제한, 업로드 용량 제한, 파일 다운로드 준비 흐름은 문법/테스트 검증까지 완료했다.

---

## 다운로드 UX 단순화 및 AI 추가 요청

- [x] 파일/ZIP/PDF 다운로드 준비 버튼 제거 범위 확인
- [x] 웹하드 파일은 클릭 시점에만 다운로드되도록 변경
- [x] ZIP/PDF/메모 ZIP을 원버튼 다운로드로 정리
- [x] AI 답변 아래 추가 요청 입력과 대화 다운로드 추가
- [x] 테스트와 문법 검증 실행
- [x] 변경 요약 작성

## 요약
- 웹하드 개별 파일은 GCS signed URL 버튼으로 바꿔 사용자가 `다운로드`를 누를 때만 브라우저가 파일을 받도록 했다.
- 웹하드 ZIP, 메모 ZIP, AI 결과 PDF/대화 PDF, MD to PDF 도구는 준비 버튼 없이 바로 다운로드 버튼이 보이도록 정리했다.
- AI 답변 아래에 추가 요청 입력과 전송 버튼을 추가해 이전 대화 맥락을 이어서 질문하고, 전체 대화 PDF도 받을 수 있게 했다.

---

## AI 저장/프롬프트/추가 요청 보정

- [x] AI 결과 PDF를 웹하드에 저장하는 버튼 추가
- [x] 프롬프트 일괄 추가 버튼 추가
- [x] 추가 요청 버튼 활성화 흐름 개선
- [x] 테스트와 문법 검증 실행
- [x] 변경 요약 작성

## 요약
- AI 결과 저장 영역에 `PDF로 저장(웹하드)` 버튼을 추가해 생성된 PDF를 웹하드 업로드 경로에 저장하도록 했다.
- 프리셋 영역에 `프롬프트 일괄 추가` 버튼을 추가하고, 이미 선택된 프리셋은 중복 추가하지 않게 했다.
- 추가 요청 버튼은 입력값 때문에 늦게 활성화되지 않도록 API/한도 조건만으로 활성화하고, 빈 입력은 클릭 시 안내하도록 바꿨다.

---

## AI 예상비용 분석 도구 추가

- [x] Gemini usage 로그 구조 확인
- [x] 도구모음에 AI 비용 분석 도구 추가
- [x] 비용 막대그래프와 요약 지표 추가
- [x] CSV 다운로드 추가
- [x] 테스트와 문법 검증 실행
- [x] 변경 요약 작성

## 요약
- 도구모음에 `AI 예상비용` 도구를 추가해 Gemini 사용량 로그를 최근 7일, 최근 30일, 전체 범위로 볼 수 있게 했다.
- 총 예상 비용, 요청 수, 전체 토큰, 요청당 평균 비용을 지표로 보여주고 날짜별 예상 비용을 막대그래프로 표시한다.
- 날짜별 요약 CSV와 상세 로그 CSV 다운로드를 추가하고, 날짜별 비용 집계 테스트를 보강했다.

---

## 새 프론트엔드 UI API 연결

- [x] 세션 상태 표시를 상단 인증 영역에 추가
- [x] 웹하드 목록, 업로드, 다운로드, 삭제를 API에 연결
- [x] 메모 목록, 저장, 상세 보기, 삭제를 API에 연결
- [x] 파일 ZIP, 메모 ZIP 다운로드 endpoint와 버튼 연결
- [x] AI 분석 버튼을 Gemini API endpoint에 연결
- [x] 모바일 인증 버튼 배치와 상태 문구 정리
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 새 프론트엔드는 `/api/session`, `/api/files`, `/api/memos`를 우선 사용하고, 인증 전에는 데모 데이터를 유지한다.
- 패스키 또는 Google Access 인증 상태가 상단 chip에 표시되며, 파일/메모/AI 작업 실패는 toast로 안내한다.
- 파일 ZIP, 메모 ZIP, 프롬프트 기반 Gemini 분석은 Starlette API endpoint로 연결했다.
- Playwright 모듈이 없어 브라우저 screenshot 검증은 실행하지 못했고, 로컬 HTTP 응답과 JS 문법/유닛 테스트로 1차 확인했다.

---

## 새 프론트엔드 마감 개발

- [x] 파일 검색과 표시 개수 상태 추가
- [x] 메모 검색과 선택 메모 편집 흐름 추가
- [x] AI 분석 결과를 메모로 저장하는 버튼 추가
- [x] 인증 전/후 버튼 상태와 빈 화면 정리
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 파일/메모 검색 input과 표시 개수 상태를 추가했다.
- 메모를 열면 작성 폼에 들어와 수정 저장할 수 있고, 현재 편집 중인 메모를 목록에서 강조한다.
- AI 분석 결과를 바로 메모로 저장할 수 있게 했다.
- `node --check`, `py_compile`, unittest 22개, 로컬 HTTP 200/401/owner session 응답을 확인했다.

---

## 도구모음 프론트엔드 완성

- [x] 도구모음 카드 클릭 시 작업 패널 표시
- [x] 텍스트 클리너, 글자수 카운터, 정산 계산기 로컬 동작 추가
- [x] MD to PDF API endpoint와 다운로드 버튼 연결
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 도구모음의 정적 카드들을 실제 작업 패널로 전환했다.
- MD to PDF endpoint는 인증 전 401로 막히고, 프론트 HTML은 200으로 응답함을 확인했다.

---

## AI 소스 선택 마감

- [x] AI 분석에 파일 선택 목록 추가
- [x] AI 분석에 메모 선택 목록 추가
- [x] 선택한 파일/메모를 `/api/ai/analyze` payload로 전달
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 인증 후 로드된 GCS 파일과 메모를 AI 분석 소스로 선택할 수 있게 했다.
- 선택된 GCS blob과 memo file name은 서버에서 다시 조회해 Gemini 분석 context로 전달한다.
- `node --check`, `py_compile`, unittest 22개, 로컬 HTTP 200/401/owner session 응답을 확인했다.

---

## 프론트엔드 지표 실데이터 연결

- [x] AI usage summary API 추가
- [x] 상단 AI 비용/모델 표시를 usage summary에 연결
- [x] AI 분석 완료 후 비용 지표 갱신
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 하드코딩된 이번 달 AI 비용 문구를 제거하고 Gemini usage 로그 기반 summary를 표시하도록 바꿨다.
- `node --check`, `py_compile`, unittest 22개, 로컬 HTTP 200/401/owner session 응답을 확인했다.

---

## 프론트엔드 문구 및 미리보기 정리

- [x] hero 파일/메모 미리보기를 현재 상태 기반으로 갱신
- [x] `Preview`, `Ver 5`, `최근 500건` 등 오래된 문구 제거
- [x] README와 frontend README를 Starlette API 운영 기준으로 갱신
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 상단 hero mock count와 최근 항목이 실제 파일/메모 state를 따라가게 했다.
- 프론트엔드 문서와 화면 문구를 Cloud Run, Cloudflare Access, Passkey, GCS, Gemini 기준으로 정리했다.
- `node --check`, `py_compile`, unittest 22개, 로컬 HTTP 200/401, stale preview 문구 제거 확인을 완료했다.

---

## 프론트엔드 HTML 분리

- [x] 홈/지표 영역을 `frontend/partials/home.html`로 분리
- [x] 웹하드 영역을 `frontend/partials/files.html`로 분리
- [x] 메모장 영역을 `frontend/partials/memos.html`로 분리
- [x] AI 영역을 `frontend/partials/ai.html`로 분리
- [x] 도구모음 영역을 `frontend/partials/tools.html`로 분리
- [x] `api_server.py`에서 include 주석 기반 HTML 조립 추가
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- `index.html`은 shell 역할만 하도록 줄이고, 기능별 HTML partial을 서버에서 조립하도록 바꿨다.
- `py_compile`, `node --check`, `unittest 22개`, 로컬 `/` HTTP 200 및 partial 조립을 확인했다.

---

## Access OTP 제거 방향 인증 전환

- [x] Cloudflare Access 필수 요구를 기본 off로 전환
- [x] 패스키 등록/로그인을 소유자 이메일 기준으로 동작하게 정리
- [x] 계정 ID fallback 세션 API 추가
- [x] 프론트엔드 인증 버튼을 `패스키 + 계정 ID` 흐름으로 변경
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- Cloudflare Access 헤더가 있으면 계속 인정하되, 이메일 OTP가 앱 진입을 막지 않도록 앱 자체 인증을 1차 경계로 바꾼다.
- `py_compile`, `node --check`, unittest 25개, 로컬 계정 ID 로그인/세션/API 200 응답을 확인했다.

---

## 프론트엔드 화면 라우팅 및 설정 분리

- [x] 홈/웹하드/메모장/AI/도구모음을 경로 기반 단일 화면으로 전환
- [x] 설정 화면을 새 창에서 열 수 있게 추가
- [x] 계정 ID 로그인 UI를 설정 화면으로 이동
- [x] 접속 기록 분석 API와 설정 패널 추가
- [x] Gemini 토큰/비용 분석 API와 설정 패널 추가
- [x] 문법, 테스트, 로컬 HTTP 검증

## 요약
- 섹션 anchor 스크롤 대신 `/files`, `/memos`, `/ai`, `/tools`, `/settings` 경로로 화면을 전환한다.
- `py_compile`, `node --check`, unittest 25개, 로컬 `/files`/`/settings` 200, 설정 분석 API 응답을 확인했다.

---

## 실사용 UX 보강

- [x] 계정 ID fallback을 ID + 비밀번호 로그인으로 변경
- [x] 패스키 등록을 로그인 후 등록 흐름으로 제한
- [x] AI 분석 결과를 마크다운으로 렌더링
- [x] AI 결과 MD/PDF 다운로드 버튼 연결
- [x] AI 파일 선택 제목 색상 수정
- [x] 도구모음에서 저장소/접속 상태 제거 후 설정으로 이동
- [x] 최근 메모 본문 스크롤과 현재 메모 TXT 다운로드 추가
- [x] 웹하드 파일 선택 즉시 업로드
- [x] 업로드 파일명에서 날짜/시간 suffix 제거 및 업로드 시각은 metadata로 저장
- [x] 문법과 단위 테스트 검증
- [x] 제한 없는 로컬 HTTP 검증

## 요약
- 실사용 흐름 기준으로 인증, AI 결과물, 메모/파일 동작을 정리한다.
- `node --check`, `py_compile`, unittest 26개를 확인했고, 로컬 API 서버를 띄워 `/`, `/files`, `/memos`, `/ai`, `/tools`, `/settings`, `/api/session`, `/api/health` 응답을 확인했다.

---

## GCS Cloud Run 빌드 설정 정리

- [x] `cloudbuild.yaml` 배포 환경변수를 현재 GCS/Passkey/ID+비번 인증 기준으로 갱신
- [x] 계정 비밀번호를 Cloud Run Secret Manager 주입값으로 변경
- [x] Dockerfile에 Python 런타임 기본 env 추가
- [x] 배포 문서의 env/secret 목록 갱신
- [x] 빌드 설정 문법 및 정적 검증
- [x] Docker daemon 연결 후 실제 이미지 빌드 검증

## 요약
- Cloud Build가 더 이상 Cloudflare OTP 필수/Google Access fallback 기준으로 배포하지 않게 정리한다.
- `cloudbuild.yaml` YAML 파싱, `py_compile`, `node --check`, unittest 26개를 확인했고, 실제 `docker build -t jisong-cloud:test .`까지 성공했다.

---

## 상단바 구조 개선 및 상태 표시 최적화

- [x] 상단바(`global-nav`) 레이아웃 재구성 (왼쪽: 브랜드/링크, 중앙: 검색, 오른쪽: 시스템 정보/상태)
- [x] 시스템 정보(현재 시간, 접속 IP) 표시 기능 추가
- [x] 하단바(`sub-nav`) 간소화 (인증 칩 제거, 설정을 아이콘으로 변경)
- [x] 전역 검색 필드 구현 및 파일/메모 필터링 연동
- [x] 로그인 상태 및 인증 방식 시각화 개선 (상단바 이동)
- [x] 실시간 시계 기능 구현

## 요약
- 상단바에 로그인 상태, 패스키 등록, 시간, IP, 검색 기능을 통합하여 접근성을 높였습니다.
- 하단바의 불필요한 인증 관련 요소들을 제거하고 설정을 아이콘으로 간소화했습니다.
- 로그인 상태가 실시간으로 반영되도록 `setSessionChip` 로직을 고도화했습니다.

---

## 패스키 및 GCS 연동 오류 수정

- [x] GCS 클라이언트 설정 개선 (`secrets.toml` 직접 파싱 지원)
- [x] 패스키 관련 엔드포인트 디버그 로그 추가
- [x] 패스키 로그인 옵션 오류 코드 최적화 (404 처리)
- [ ] 패스키 동작 최종 확인

## 요약
- `User project invalid` 오류 해결을 위해 `gcs_helper.py`에서 서비스 계정 정보를 `secrets.toml`에서 직접 로드하도록 수정했습니다.
- `uvicorn` 환경에서도 설정을 정확히 읽어올 수 있도록 `config.py`에 TOML 직접 파싱 로직을 추가했습니다.
- 패스키 로그인 시 발생하던 400 오류의 원인을 파악하기 위해 상세 디버그 로그를 추가했습니다.
- 로컬 API에서 `/api/auth/passkey/login/options`는 현재 `404 {"error":"등록된 passkey가 없습니다."}`를 반환해, 실제 패스키 등록자 없이는 최종 end-to-end 확인이 불가능한 상태입니다.

---

## Mac folder sync + CSV 분리 설계

- [x] Mac `Developer` 폴더를 source of truth로 두는 파일 sync 구조 설계
- [x] MongoDB 대신 CSV로 환자 검사정보를 분리하는 방향 정리
- [x] sync worker, conflict 규칙, schema 초안 문서화
- [x] local folder watcher와 sync queue 구현
- [x] CSV schema와 file reference 모델 구현
- [x] UI에서 sync 상태와 conflict copy 노출

## 요약
- 파일은 Mac 폴더와 GCS mirror로 두고, 환자 검사정보는 CSV로 우선 분리하는 구조로 정리했다.
- MongoDB는 문서 저장에는 쓸 수 있지만, 이 프로젝트의 핵심 문제인 파일 동기화와 충돌 처리에는 맞지 않는다.
- 구현은 watcher, queue, CSV schema 순으로 쪼개는 게 안전하다.

- [x] Gemini 모델을 `gemini-3-flash-preview`로 변경
- [x] 프론트엔드 영문 폰트(Inter/Outfit)를 제거하고 Apple SD Gothic Neo 등의 시스템 폰트로 일괄 적용
- [x] 프론트엔드 CRUD의 더미 데이터 Fallback 로직을 완전히 제거하여 실제 데이터를 정상적으로 불러오도록 개선
- [x] 메인 UI(하단바/서브 네비게이션)의 구름 아이콘을 로그인 화면과 동일한 그라데이션 SVG 아이콘으로 교체

---

## UI 및 안정성 개선

- [x] 웹하드 및 메모장 레이아웃을 1열(single column)로 변경하여 파일 올리기와 새 메모 UI가 상단에 고정되도록 수정
- [x] 도구모음 내 텍스트 클리너 UI 깨짐 현상 수정 (`pre` 태그 줄바꿈 속성 추가)
- [x] `cloudbuild.yaml`에서 누락된 Secret 환경 변수(`JISONG_ACCOUNT_PASSWORD`)를 환경 변수로 이동시켜 배포 오류 해결
- [x] 설정 화면에 Gemini 요금 설정(비용 배율 및 환율) 기능을 추가하고, 사용량 분석 API에서 동적으로 반영되도록 개선

## 요약
- 배포 시 발생하던 빌드 오류를 수정하여 안정적으로 Cloud Run에 배포되도록 조치했습니다.
- 웹하드와 메모장의 레이아웃을 1열로 변경하여 사용자 접근성을 크게 향상시켰습니다.
- 텍스트 클리너 도구의 UI가 텍스트 길이에 따라 깨지지 않도록 줄바꿈 처리를 보강했습니다.
- Gemini API 비용을 추산할 때 사용자가 직접 설정 화면에서 배율과 환율을 조정할 수 있도록 프론트엔드/백엔드 로직을 확장했습니다.

---

## 프로젝트 전반 개선 마무리

- [x] 세션 실패 시 UI 인증 상태 초기화
- [x] 프록시 헤더 기준 클라이언트 IP 추출
- [x] 계정 비밀번호의 코드 기본값 제거
- [x] 접속/GCS/설정 오류 로깅 구조화
- [x] GCS 로그 경로 중복 제거
- [x] 네트워크 의존 테스트를 단위 테스트로 교체
- [x] 스트림릿 포커스 스크립트 호환성 보정
- [x] Gemini 설정 저장 후 갱신 경로 정리
- [x] 도구 패널을 별도 모듈로 분리

## 요약
- 실제 사용자 영향이 있는 런타임/운영 문제를 먼저 정리했다.
- 코드 기본값과 중복 경로를 제거해 인증과 로그의 단일 출처를 맞췄다.
- 도구 패널 분리로 `frontend/app.js`의 책임을 줄였다.

---

## Gemini 설정 오류 수정

- [x] `/Users/jsbang/.gemini/settings.json`의 `general.defaultApprovalMode` 값을 `"default"`로 수정
- [x] `gemini` CLI 실행을 통해 설정 오류 해결 여부 검증

## 요약
- `~/.gemini/settings.json`의 `general.defaultApprovalMode` 값이 지원되지 않는 `"auto"`로 설정되어 있어 CLI 실행 시 발생하던 검증 에러를 수정했습니다.
- 유효한 값인 `"default"`로 설정을 변경하여 configuration 파싱 에러를 완벽히 해결했습니다.


---

## v6 Core Philosophy 및 아키텍처 재설계 기반 로드맵
*(EMR 정제 파이프라인 및 Local-first 브릿지 지향)*

### Phase 1: Data Pipeline & Workspace Structure
- [x] **Patient-centric Workspace 구조 적용:** `workspace/patient_ID/{labs, medications, imaging, pathology, notes}` 디렉토리 구조 확립 및 경로 빌더 연동
- [x] **모든 문서(MD/CSV) Metadata 필수 첨부 강제화:** (type, date, tags, source 등)

### Phase 2: Frontend Redesign & Sync Integration
- [x] **Drag-and-Drop Intake UI 개편:** 범용 AI 챗봇 UI를 대폭 축소하고, EMR 텍스트/파일을 던져넣는(Ingestion) 유틸리티 인터페이스로 전환
- [x] **Document Preview & Metadata Editing UI 구현:** 파싱된 결과를 로컬로 넘기기 전 검수하고 메타데이터를 수정하는 뷰어 추가
- [x] **Local Sync Daemon 연동 기반 마련:** GCS와 로컬 Mac(`~/Developer/jisong_workspace/`) 간의 동기화 모니터링 UI

### Phase 3 & 4: Local Mac Ecosystem Handoff
- [x] **메타데이터 인덱싱 및 시각화용 Export 정비**
- [x] **Local AI (Ollama) 및 Semantic Search 연동 Hook 구성:** 로컬 Obsidian 및 Python 환경에서 후처리가 용이하도록 데이터 포맷 완결성 보장
