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
- 도구모음 선택 버튼은 상태 변경 직후 `_select_tool()`에서 즉시 `st.rerun()` 하도록 바꿔서 화면 전환 체감이 더 빠르게 반영되도록 정리했다.
- 웹하드, 메모장, 접속 기록 관리의 전체 삭제 버튼에 전용 key를 부여하고, 전역 CSS에서 해당 key만 빨간 강조 버튼으로 스타일링했다.
- 문법 검증과 diff 검사로 도구 전환 로직과 Danger 버튼 스타일이 기존 동작을 깨지 않는지 확인했다.
