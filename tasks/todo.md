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
