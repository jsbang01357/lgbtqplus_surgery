# parser-core 보류 메모

`parser-core/`는 이전 EMR normalization 실험에서 넘어온 TypeScript 모듈입니다. 현재 Qplus Surgery 오프라인 수술 일정 대시보드의 필수 실행 경로는 아닙니다.

## 현재 상태

- 위치: `parser-core/`
- 언어: TypeScript
- package name: `@qplus-surgery/parser-core`
- 현재 FastAPI 라우터에는 parser-core endpoint가 연결되어 있지 않습니다.
- Dockerfile은 아직 parser-core install/build를 수행합니다.

## 현재 운영 판단

오프라인 수술 일정 운영에는 아래 기능이 우선입니다.

- 수술 케이스 CRUD
- 상태 자동 계산
- CSV import/export
- 로컬 파일 저장소
- 계정/권한/백업

따라서 parser-core는 지금 당장 개선 대상이 아닙니다.

## 다시 활성화할 조건

아래 요구가 명확해지면 별도 작업으로 재검토합니다.

- EMR 텍스트를 수술 일정/프리메드 항목으로 자동 분해해야 한다.
- 검사/협진/처방/영상/병리 기록을 구조화해야 한다.
- AI 또는 rule-based parser 결과를 UI에서 검수해야 한다.

## 재개 시 정리할 것

- package name을 Qplus Surgery 기준으로 변경
- FastAPI bridge 필요 여부 결정
- Dockerfile에서 parser-core build가 필수인지 분리
- TypeScript 의존성 설치와 `npm run check` 검증 복구
- parser output schema를 수술 케이스 schema와 분리

## 지금의 권장 조치

운영 배포가 parser-core 때문에 느려지거나 실패하면 Dockerfile에서 parser-core build를 선택 단계로 분리합니다. 다만 현재 변경은 오프라인 저장소 전환과 문서 정리에 집중하므로 Docker 구조 개편은 별도 작업으로 둡니다.
