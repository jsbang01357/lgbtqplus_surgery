# JisongCloud v6 Parser Core Plan

## 목적

JisongCloud v6의 핵심은 웹 AI surface가 아니라 EMR normalization engine이다.  
따라서 parser는 UI 컴포넌트가 아니라 독립 TypeScript 코어로 유지한다.

## Clean_Text inventory

참조 레포: `https://github.com/jsbang01357/Clean_Text`

재사용 우선순위:

1. `emr_tools/frontend/src/core/labParser.ts`
2. `emr_tools/frontend/src/core/textCleaner.ts`
3. `emr_tools/frontend/src/core/excelExporter.ts`
4. `emr_tools/frontend/src/TableConverterApp.tsx`

정리 기준:

- `core/*.ts`: parser-core 후보
- `*.tsx`: review UI 후보
- Excel exporter: v6에서는 CSV writer 우선, Excel은 후순위

## v6 parser-core 범위

현재 추가된 모듈:

- `schemas/`: modality별 typed schema
- `core/textNormalizer.ts`: Clean_Text의 EMR cleaning heuristic 일부 이식
- `splitters/emrChunkSplitter.ts`: large blob chunk 분리
- `classifiers/modalityClassifier.ts`: modality 판정
- `parsers/`: lab/medication/imaging/pathology/note parser entry
- `writers/`: markdown/csv/frontmatter renderer
- `pipeline/runNormalizationPipeline.ts`: end-to-end orchestration

## 다음 단계

1. `Clean_Text`의 `labParser.ts` 세부 케이스를 v6 `parseLabChunk.ts`로 더 이식
2. medication parser에 날짜/route/frequency/status 변경 추적 강화
3. imaging/pathology/note parser에 section boundary heuristic 보강
4. artifact path builder와 `SyncManifestEntry` writer 추가
5. Starlette `/api/v6/health`, `/api/v6/parse` 브리지 추가
6. review UI는 별도 TSX surface로 분리
7. chunk precision과 mixed-document separation heuristic 보강

## 설계 원칙

- parser output은 사람이 읽을 수 있는 `csv` / `md`
- local workspace가 canonical source
- cloud는 staging + normalization + manifest publish까지만 담당
- AI fallback은 low-confidence chunk에만 제한적으로 사용

## 현재 연결 상태

- `app/v6_bridge.py`: Python -> Node CLI bridge
- `api_server.py`: `/api/v6/health`, `/api/v6/parse`
- `Dockerfile`: Node runtime 설치 + `parser-core` build 수행

현재는 API bridge까지 연결됐고, parser 품질 고도화와 review UI가 다음 우선순위다.
