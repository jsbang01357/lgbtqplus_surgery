# 🧠 Lessons Learned

Use this file to record patterns when a mistake is corrected.
Reuse these lessons in future tasks to avoid repeating the same mistakes.

---

## Parsing Edge Cases
* 마크다운 변환 중 임시 placeholder를 둘 때는 `_`, `*`, `` ` ``처럼 이후 정규식이 다시 해석할 수 있는 문자를 피한다.

## Formatting Errors
* (Add learned patterns here...)

## Missed Requirements
* 작업 체크리스트를 갱신할 때는 새 파일로 덮어쓰기 전에 기존 `tasks/todo.md` 내용을 먼저 확인하고, 이전 기록 아래에 새 작업 섹션을 추가한다.
* 앱의 진입점이 바뀌면 README의 실행 방법, 구조도, 인증 설명부터 먼저 다시 확인한다. 이 저장소는 Streamlit 보조 모듈이 남아 있어도 운영 기준 진입점은 `api_server.py`다.
* 제거 예정 API 경고를 처리할 때는 기능 삭제 전에 실제 사용자 가치와 fallback 가능성을 먼저 확인한다.
* Streamlit 세션 상태로 다운로드 bytes를 준비할 때는 source 플래그를 먼저 갱신해 생성 조건을 건너뛰지 않도록 한다.
* 한국어 인명 마스킹 정규식은 `환자는`처럼 명사 뒤 조사가 붙는 케이스까지 테스트한다.
* 도메인명이 바뀌면 코드, 환경 샘플, 운영 문서, 작업 요약에 남은 이전 도메인 문자열을 함께 검색해 정리한다.
* GCS 기반 저장소를 쓰는 테스트는 `get_bucket()`나 `list_blobs()`를 직접 호출하지 말고, 기본은 skip 또는 mock으로 두고 통합 테스트만 별도 opt-in으로 분리한다.
* 현재 코드가 GCS로 세션을 저장하면 예전의 in-memory 세션 global을 전제로 한 테스트 정리는 깨진다. `_load_*` / `_save_*`를 patch해서 로컬 상태를 주입해야 한다.
* UI 저장 버튼처럼 즉시 반응하는 콜백은 존재하지 않는 후속 함수를 부르면 화면은 살아 보여도 콘솔 에러가 난다. 저장 직후 갱신 경로는 실제 정의된 함수만 연결한다.
* 화면에서 사라진 레거시 DOM 셀렉터는 바인딩만 남겨도 실제 동작은 안 바뀌지만 유지보수 잡음을 만든다. 존재하지 않는 `querySelector`는 같이 제거한다.
* 큰 프론트엔드 파일을 나눌 때는 렌더링 템플릿만 빼는 것으로 끝내지 말고, 호출부의 deps 전달도 함께 정리해야 분리 효과가 유지된다.
* 런타임 호환 컴포넌트(`streamlit_compat.py` 등)를 새로 사용하도록 코드를 리팩토링할 때는 호출부 파일(`auth.py` 등)에서 해당 함수(`render_inline_html`)가 올바르게 임포트되었는지 꼼꼼하게 교차 검증해야 한다.
* Starlette 버전에 따라 `Starlette(..., on_startup=..., on_shutdown=...)`가 지원되지 않을 수 있으니, background service 연결은 `lifespan`으로 묶는 쪽을 우선 확인한다.
