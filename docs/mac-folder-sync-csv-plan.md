# Mac Folder Sync 계획 보류 메모

이 문서는 이전 개인 클라우드 계열의 Mac 폴더 동기화 계획을 Qplus Surgery 기준으로 정리한 보류 메모입니다.

## 현재 판단

Qplus Surgery의 현재 핵심은 수술 일정 운영입니다. 파일 동기화 worker, Mac 폴더 mirror, CSV 기반 진료자료 저장소는 지금 당장 운영 필수 기능이 아닙니다.

현재 우선순위:

1. 로컬 파일 저장소 기반 수술 일정 CRUD 안정화
2. CSV import/export 품질 유지
3. `.local_data/storage/` 백업/복구 체계
4. 사용자/권한 관리

## 지금 하지 않는 것

- Mac 전체 폴더 watcher
- GCS mirror worker
- 파일 conflict resolver
- exam/patient 파일 메타데이터 CSV schema
- MongoDB 또는 별도 DB 도입

## 나중에 다시 볼 조건

아래 요구가 실제로 생기면 별도 설계로 재검토합니다.

- 수술 일정 외의 문서/검사/이미지 파일 관리가 필요하다.
- 여러 장비에서 같은 파일 묶음을 편집한다.
- 파일 변경 이력과 conflict 처리가 운영상 필요하다.
- 단순 CSV import/export로 감당하기 어려운 문서 워크플로가 생긴다.

## 재검토 시 원칙

- 수술 일정 저장소와 파일 sync 저장소를 섞지 않습니다.
- 로컬에서 복구 가능한 단순 구조를 우선합니다.
- conflict는 자동 덮어쓰기하지 않습니다.
- 운영자가 이해할 수 없는 동기화 추상화는 만들지 않습니다.
