# JisongCloud v6 Parser Core

`parser-core`는 JisongCloud v6의 EMR 정규화 엔진입니다.

원칙:

- UI와 분리된 순수 TypeScript 코어
- heuristic-first parsing
- modality별 typed output
- markdown/csv 중심 artifact generation
- local-first sync를 위한 manifest-friendly metadata

현재 범위:

- EMR text normalization
- chunk splitting
- chunk modality classification
- lab / medication / imaging / pathology / clinical note parser 골격
- markdown / csv writer

원본 참조:

- `Clean_Text/emr_tools/frontend/src/core/labParser.ts`
- `Clean_Text/emr_tools/frontend/src/core/textCleaner.ts`

v6에서는 이 로직을 UI 컴포넌트가 아니라 reusable parser engine으로 옮기는 것이 목표입니다.
