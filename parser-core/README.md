# Qplus Surgery parser-core

이 TypeScript 모듈은 EMR text normalization 실험용 코어입니다. 현재 Qplus Surgery 오프라인 수술 일정 대시보드의 필수 실행 경로는 아닙니다.

## 현재 상태

- 앱의 기본 CRUD/API/UI는 Python FastAPI와 정적 프론트엔드만으로 동작합니다.
- parser-core는 현재 라우터에 직접 연결되어 있지 않습니다.
- 필요할 때만 별도로 의존성을 설치하고 검증합니다.

## 검증

```bash
npm ci
npm run check
```

## 재개 조건

아래 요구가 생기면 별도 작업으로 다시 활성화합니다.

- EMR 텍스트에서 검사/협진/프리메드 정보를 구조화해야 한다.
- 수술 케이스 입력을 자동 보조해야 한다.
- parser 결과를 UI에서 검수하는 workflow가 필요하다.

## 주의

오프라인 운영 배포가 목표라면 parser-core 빌드를 필수 경로에 두지 않는 것이 좋습니다.
