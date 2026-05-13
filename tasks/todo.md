## Streamlit 경고 및 모바일 UI 보정

- [x] `components.html` 사용 제거 여부 판단
- [x] 로그인/메모 자동 포커스 스크립트 유지 및 fallback 적용
- [x] idle timeout JS 주입 유지 및 fallback 적용
- [x] 모바일 사이드바 상태 박스 높이 보정
- [x] 로그인 폼 카드 여백 보정
- [x] AI 결과 PDF 준비 버튼 상태 갱신 수정
- [x] 기본 검증

## 요약
- 자동 포커스와 비활성 자동 창 닫기는 유지하되, `components.html`이 없어져도 앱 전체가 죽지 않도록 호환 렌더링 함수를 거치게 했다.
- 모바일 사이드바 상태 박스는 고정 배치를 해제하고, 로그인 폼은 하단 여백을 늘렸다.
- AI 결과 PDF는 준비 버튼을 누른 같은 실행 흐름에서 bytes를 생성하고 다운로드 버튼으로 전환되게 했다.

---

## 운영 안정성 개선

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

## 프로젝트 전반 개선점 점검

- [x] 현재 작업트리와 주요 파일 구조 확인
- [x] AI, 저장소, 메모, 도구, 배포 설정 점검
- [x] 테스트/문법 검증 실행
- [x] 우선순위별 개선점 요약

## 요약
- 현재 작업트리는 `app/ai.py`와 `tasks/todo.md` 변경만 남아 있다.
- 기본 테스트와 문법 검증은 통과했다.
- 우선 개선점은 GCS JSON 로그 동시 쓰기, ZIP 메모리 사용, HTML escaping, 비용 설정값 분리, 테스트 커버리지 확장이다.

---

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
