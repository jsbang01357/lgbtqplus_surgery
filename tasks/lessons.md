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
* 제거 예정 API 경고를 처리할 때는 기능 삭제 전에 실제 사용자 가치와 fallback 가능성을 먼저 확인한다.
* Streamlit 세션 상태로 다운로드 bytes를 준비할 때는 source 플래그를 먼저 갱신해 생성 조건을 건너뛰지 않도록 한다.
* 한국어 인명 마스킹 정규식은 `환자는`처럼 명사 뒤 조사가 붙는 케이스까지 테스트한다.
