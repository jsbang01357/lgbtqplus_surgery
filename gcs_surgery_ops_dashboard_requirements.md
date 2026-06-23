# GCS Surgery Ops Dashboard 요구사항 정리

문서 버전: v0.1  
작성일: 2026-06-23  
기반 프로젝트: `jsbang01357/jisong_cloud` fork/분기 예정  
목표 배포 형태: FastAPI + 정적 프론트엔드 + Google Cloud Storage + Cloud Run

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

교수님이 전달한 수술 일정/준비 현황 관리 화면을 Notion/Make 자동화가 아니라, GCS 기반 웹앱으로 구현한다.

이 앱은 수술 예정 환자별로 다음 정보를 한 화면에서 확인하고 관리하는 것을 목표로 한다.

- 이번 주 수술 일정
- 수술 준비 완료 여부
- 확인 필요 환자
- 누락된 준비 항목
- 수술방, 마취, 입원 여부
- Google Calendar 연동 상태
- 집도의별 수술 건수
- 취소/변경 이력

### 1.2 핵심 방향

기존 `jisong_cloud` 구조를 fork 또는 복제하여 다음 구조를 재사용한다.

- FastAPI API server
- 정적 frontend serving
- Google Cloud Storage 저장 구조
- Cloud Run 배포 구조
- 기존 인증 경계 일부 재사용

단, 환자 정보가 들어갈 가능성이 있으므로 개인용 `jisong_cloud`와는 서비스, 버킷, 접근 권한을 분리하는 방향을 원칙으로 한다.

---

## 2. 원 요구사항 요약

교수님 전달 자료 기준 요구사항은 다음과 같다.

### 2.1 상단 영역

- Google Calendar 연동 상태 표시
- 노션-구글 캘린더 Make 자동화 시나리오에 해당하는 연동 구조를 웹앱 내에서 재해석
- 이번 주 수술 현황 요약 카드 5개 표시
  - 전체
  - 준비완료
  - 확인필요
  - 진행중
  - 취소
- 확인 필요 환자 자동 경보 배너 표시

### 2.2 메인 테이블

- 확인 필요 환자를 최상단에 우선 노출
- 누락 항목 태그 표시
- 이번 주 수술 일정 전체 표시
- 표시 항목에 수술방, 마취, 입원 여부 포함

### 2.3 우측 사이드바

- 8개 필수 보기 바로가기
- 각 보기별 미완료 카운트 뱃지 포함
- 집도의별 이번 주 수술 건수 요약

### 2.4 하단 자료표 구조

- 4개 DB 구조를 한눈에 파악할 수 있어야 함
  - 수술 기본
  - 준비 현황
  - 캘린더 연동
  - 취소 이력
- 자동 상태 분류 기준 표시
  - 수술 2주 전 완료 기준
  - 8주 이내 검사 기준

---

## 3. 웹앱으로 변환한 제품 요구사항

### 3.1 제품명 후보

- Surgery Ops Cloud
- Surgery Board Cloud
- GCS Surgery Ops Dashboard

### 3.2 사용자

초기 사용자 후보는 다음과 같다.

- 교수님
- 코디네이터
- 간호사
- 수술 일정 관리 담당자
- 개발/운영 관리자

### 3.3 핵심 사용 시나리오

#### 시나리오 1. 이번 주 수술 현황 확인

사용자는 대시보드 상단에서 이번 주 수술 건수를 확인한다.

- 전체 수술 수
- 준비완료 수
- 확인필요 수
- 진행중 수
- 취소 수

#### 시나리오 2. 확인 필요 환자 확인

사용자는 확인 필요 환자 경보 배너와 메인 테이블 상단에서 준비 미완료 환자를 확인한다.

각 환자에는 누락 항목 태그가 표시된다.

예시:

- 검사 없음
- 검사 유효기간 초과
- 마취평가 미완료
- 입원 여부 미정
- 동의서 미완료
- 수술 전 설명 미완료
- 금식 안내 미완료
- 캘린더 미연동
- 캘린더 오류

#### 시나리오 3. 수술 케이스 입력/수정

사용자는 수술 케이스를 새로 입력하거나 수정한다.

입력 항목:

- 환자 코드
- 수술일
- 시작 시간
- 종료 시간
- 수술명
- 집도의
- 수술방
- 마취
- 입원 여부
- 검사 시행일
- 준비 항목 완료 여부
- 캘린더 연동 상태
- 비고

#### 시나리오 4. 취소/변경 이력 관리

사용자는 수술 취소 또는 일정 변경을 기록한다.

기록 항목:

- 취소 여부
- 취소 사유
- 기존 수술일
- 변경 후 수술일
- 기록일
- 기록자
- 비고

#### 시나리오 5. Google Calendar 연동 상태 확인

초기 MVP에서는 실제 Google Calendar API 연동 없이 연동 상태만 관리한다.

추후 2차 버전에서 Google Calendar API를 붙인다.

---

## 4. 시스템 구조

### 4.1 전체 아키텍처

```text
Browser
  |
  v
Cloud Run
  |
  v
FastAPI app
  |
  +-- Static frontend
  +-- /api/surgery/*
  |
  v
Google Cloud Storage
```

### 4.2 기존 `jisong_cloud`에서 재사용할 부분

재사용 대상:

- `api_server.py`의 FastAPI 앱 구조
- frontend 정적 파일 serving 방식
- `app/routers/*` router 분리 패턴
- GCS helper
- Dockerfile
- Cloud Build / Cloud Run 배포 구조
- 인증 관련 일부 구조

새로 추가할 부분:

```text
app/
  routers/
    surgery.py
  surgery_store.py
  surgery_status.py
  surgery_schema.py

frontend/
  partials/
    surgery.html
  surgery.js 또는 app.js 내 surgery module
```

---

## 5. GCS 저장 구조

### 5.1 권장 GCS prefix

```text
bucket/
  surgery_ops/
    cases/
    calendar/
    cancellations/
    audit/
    exports/
```

### 5.2 파일 구조

```text
surgery_ops/
  cases/
    case_20260623_001.json
    case_20260623_002.json

  calendar/
    calendar_events.json

  cancellations/
    cancellation_log.json

  audit/
    surgery_ops_audit.jsonl

  exports/
    surgery_cases_20260623.csv
```

### 5.3 데이터 저장 원칙

- MVP에서는 GCS JSON 파일 기반으로 저장한다.
- 케이스 1개당 JSON 파일 1개를 권장한다.
- 목록 조회 시 `surgery_ops/cases/` prefix를 scan한다.
- 상태값은 저장값이 아니라 조회 시 계산하는 것을 원칙으로 한다.
- audit log는 append-only JSONL 형태를 권장한다.
- 실제 환자 실명은 가능하면 저장하지 않는다.
- 환자 식별자는 환자번호 또는 내부 코드 사용을 원칙으로 한다.

---

## 6. 데이터 모델

### 6.1 Surgery Case

```json
{
  "case_id": "case_20260623_001",
  "patient_code": "P-0001",
  "patient_name": "",
  "surgery_date": "2026-06-25",
  "surgery_start_time": "09:00",
  "surgery_end_time": "11:00",
  "surgery_name": "수술명",
  "surgeon": "집도의",
  "operating_room": "OR 1",
  "anesthesia": "G/A",
  "admission_type": "입원",
  "status_manual": "",
  "calendar_status": "미연동",
  "calendar_event_id": "",
  "is_cancelled": false,
  "cancellation_reason": "",
  "notes": "",
  "prep": {
    "lab_date": "2026-06-01",
    "anesthesia_eval_done": false,
    "admission_confirmed": true,
    "consent_done": true,
    "preop_instruction_done": false,
    "fasting_instruction_done": true
  },
  "created_at": "2026-06-23T00:00:00+09:00",
  "updated_at": "2026-06-23T00:00:00+09:00"
}
```

### 6.2 계산 필드

아래 값은 저장하지 않고 조회 시 계산한다.

```json
{
  "status_auto": "확인필요",
  "missing_items": ["마취평가", "수술 전 설명", "캘린더 미연동"],
  "is_lab_valid": true,
  "days_until_surgery": 2
}
```

### 6.3 Cancellation Log

```json
{
  "case_id": "case_20260623_001",
  "cancelled_at": "2026-06-23T12:00:00+09:00",
  "reason": "환자 사유",
  "previous_surgery_date": "2026-06-25",
  "new_surgery_date": "",
  "recorded_by": "user",
  "memo": ""
}
```

### 6.4 Calendar Sync Record

```json
{
  "case_id": "case_20260623_001",
  "calendar_status": "미연동",
  "calendar_event_id": "",
  "last_synced_at": "",
  "calendar_error": ""
}
```

---

## 7. 상태 분류 기준

### 7.1 상태값

상태값은 다음 4개를 사용한다.

- 준비완료
- 확인필요
- 진행중
- 취소

### 7.2 자동 분류 규칙

우선순위는 아래 순서를 따른다.

#### 1. 취소

조건:

- `is_cancelled = true`

결과:

```text
취소
```

#### 2. 진행중

조건:

- 수술일이 오늘인 경우
- 또는 수동 상태가 진행중으로 지정된 경우

결과:

```text
진행중
```

#### 3. 확인필요

다음 중 하나라도 해당하면 확인필요로 분류한다.

- 수술일이 14일 이내인데 필수 준비 항목이 미완료
- 검사 시행일이 없음
- 검사 시행일이 수술일 기준 8주 초과
- 마취평가 미완료
- 입원 여부 미정
- 동의서 미완료
- 수술 전 설명 미완료
- 금식 안내 미완료
- Google Calendar 미연동
- Google Calendar 오류
- 필수 필드 누락

결과:

```text
확인필요
```

#### 4. 준비완료

조건:

- 취소 아님
- 오늘 수술 아님
- 필수 준비 항목 완료
- 검사 유효기간 8주 이내
- 입원 여부 확인
- 마취평가 완료
- 캘린더 연동 완료 또는 캘린더 연동을 요구하지 않는 설정

결과:

```text
준비완료
```

---

## 8. 필수 준비 항목

초기 MVP 기준 필수 준비 항목은 다음과 같다.

| 항목 | 필드명 | 타입 | 확인필요 조건 |
|---|---|---|---|
| 검사 시행일 | `lab_date` | date | 값 없음 또는 8주 초과 |
| 마취 평가 | `anesthesia_eval_done` | boolean | false |
| 입원 여부 | `admission_confirmed` | boolean | false 또는 미정 |
| 동의서 | `consent_done` | boolean | false |
| 수술 전 설명 | `preop_instruction_done` | boolean | false |
| 금식 안내 | `fasting_instruction_done` | boolean | false |
| 캘린더 연동 | `calendar_status` | select | 미연동 또는 오류 |

추후 교수님 확인 후 필수 항목은 수정 가능해야 한다.

---

## 9. API 요구사항

### 9.1 Surgery Case API

```text
GET    /api/surgery/cases
POST   /api/surgery/cases
GET    /api/surgery/cases/{case_id}
PUT    /api/surgery/cases/{case_id}
DELETE /api/surgery/cases/{case_id}
```

### 9.2 Summary API

```text
GET /api/surgery/summary
GET /api/surgery/alerts
GET /api/surgery/surgeons/summary
```

### 9.3 Cancellation API

```text
POST /api/surgery/cases/{case_id}/cancel
POST /api/surgery/cases/{case_id}/restore
```

### 9.4 CSV API

```text
GET  /api/surgery/export.csv
POST /api/surgery/import.csv
```

### 9.5 Calendar API

MVP에서는 구현하지 않는다. 필드만 먼저 둔다.

추후 구현 예정:

```text
POST /api/surgery/calendar/sync
POST /api/surgery/calendar/sync/{case_id}
GET  /api/surgery/calendar/status
```

---

## 10. Frontend 요구사항

### 10.1 Route

```text
/surgery
```

### 10.2 화면 구성

#### 상단 영역

- Google Calendar 연동 상태 표시
- 이번 주 수술 현황 카드 5개
  - 전체
  - 준비완료
  - 확인필요
  - 진행중
  - 취소
- 확인 필요 환자 자동 경보 배너

#### 메인 테이블

표시 컬럼:

- 상태
- 수술일
- 시작 시간
- 종료 시간
- 환자 코드
- 수술명
- 집도의
- 수술방
- 마취
- 입원 여부
- 누락 항목
- 캘린더 상태
- 비고
- 수정/취소 버튼

정렬 기준:

1. 확인필요 우선
2. 진행중
3. 준비완료
4. 취소
5. 수술일 오름차순

#### 우측 사이드바

필수 보기 8개:

1. 이번 주 전체
2. 확인 필요
3. 준비 완료
4. 캘린더 미연동
5. 검사 확인 필요
6. 마취평가 미완료
7. 입원 미정
8. 취소/변경 이력

각 보기에는 미완료 또는 해당 건수 뱃지를 표시한다.

#### 집도의별 요약

- 집도의명
- 이번 주 수술 건수
- 확인필요 건수

#### 하단 구조 설명

- 수술 기본 정보
- 준비 현황
- 캘린더 연동
- 취소 이력
- 자동 상태 분류 기준

---

## 11. CSV import/export 요구사항

### 11.1 Export CSV 컬럼

```text
case_id
patient_code
surgery_date
surgery_start_time
surgery_end_time
surgery_name
surgeon
operating_room
anesthesia
admission_type
lab_date
anesthesia_eval_done
admission_confirmed
consent_done
preop_instruction_done
fasting_instruction_done
calendar_status
is_cancelled
status_auto
missing_items
notes
created_at
updated_at
```

### 11.2 Import CSV 컬럼

필수 컬럼:

```text
patient_code
surgery_date
surgery_name
surgeon
```

선택 컬럼:

```text
surgery_start_time
surgery_end_time
operating_room
anesthesia
admission_type
lab_date
anesthesia_eval_done
admission_confirmed
consent_done
preop_instruction_done
fasting_instruction_done
calendar_status
notes
```

### 11.3 Import 원칙

- 실명 컬럼은 기본 import 대상에서 제외한다.
- 같은 `case_id`가 있으면 update로 처리한다.
- `case_id`가 없으면 새로 생성한다.
- import 전 preview 기능은 2차로 구현한다.

---

## 12. 보안 및 개인정보 요구사항

### 12.1 기본 원칙

- 실제 환자 실명 저장은 피한다.
- 환자번호 또는 내부 환자 코드 사용을 원칙으로 한다.
- 테스트/샘플 데이터에는 실제 환자정보를 절대 사용하지 않는다.
- GitHub repo에는 실제 환자자료를 commit하지 않는다.
- GCS bucket은 개인용 bucket과 분리하는 것을 권장한다.
- 접근 권한은 최소 권한 원칙을 따른다.

### 12.2 인증

초기 MVP 인증 후보:

- Cloudflare Access
- 앱 내부 계정 ID + 비밀번호 fallback
- Cloud Run IAM 제한

운영용 권장:

- Cloudflare Access 또는 병원/센터 계정 기반 접근 제한
- 관리자 계정과 일반 사용자 권한 분리

### 12.3 로그

audit log에 남길 항목:

- 생성
- 수정
- 삭제
- 취소
- 복구
- CSV import
- CSV export
- Calendar sync 시도
- Calendar sync 오류

로그에 실명 또는 민감 정보는 남기지 않는다.

---

## 13. Google Calendar 연동 요구사항

### 13.1 MVP 범위

MVP에서는 실제 Google Calendar API 연동을 구현하지 않는다.

대신 다음 필드를 둔다.

- `calendar_status`
- `calendar_event_id`
- `last_synced_at`
- `calendar_error`

### 13.2 2차 구현 범위

2차에서 구현할 기능:

- 수술 케이스 생성 시 Google Calendar event 생성
- 수술일/시간/수술방 변경 시 event update
- 취소 시 event 삭제 또는 제목에 `[취소]` 표시
- sync error 발생 시 앱에서 확인필요로 표시
- calendar event ID를 GCS에 저장

### 13.3 캘린더 제목 예시

환자 실명은 캘린더에 넣지 않는다.

```text
[수술] P-0001 / 수술명 / 집도의 / OR1
```

### 13.4 캘린더 설명 예시

```text
환자코드: P-0001
수술명: 수술명
집도의: 집도의
수술방: OR1
마취: G/A
입원: 입원
준비상태: 확인필요
누락항목: 마취평가, 수술 전 설명
```

---

## 14. 배포 요구사항

### 14.1 Cloud Run

권장 신규 서비스명:

```text
surgery-ops-cloud
```

### 14.2 GCS Bucket

권장 신규 bucket:

```text
surgery-ops-storage
```

빠른 데모용 대안:

```text
jisong-cloud-storage/surgery_ops/
```

단, 실제 환자정보가 들어가면 별도 bucket 사용을 원칙으로 한다.

### 14.3 환경변수

예상 환경변수:

```text
GCS_BUCKET_NAME
SURGERY_OPS_PREFIX
REQUIRE_CLOUDFLARE_ACCESS
CLOUDFLARE_ACCESS_ALLOWED_EMAILS
ALLOW_ACCOUNT_ID_FALLBACK
JISONG_ACCOUNT_LOGIN_ID
ADMIN_PASSWORD
PASSKEY_RP_ID
PASSKEY_ORIGIN
PASSKEY_RP_NAME
GOOGLE_CALENDAR_ID
```

`GOOGLE_CALENDAR_ID`는 2차 Calendar sync에서 사용한다.

---

## 15. 구현 단계

### M0. Repo 준비

목표:

- `jisong_cloud` fork 또는 복제
- 새 repo/service 이름 결정
- 로컬 실행 성공

산출물:

- 새 repo
- 로컬 FastAPI 실행
- 기존 health endpoint 확인

### M1. Surgery backend

목표:

- GCS JSON 기반 surgery case CRUD 구현

산출물:

- `app/routers/surgery.py`
- `app/surgery_store.py`
- `app/surgery_status.py`
- `/api/surgery/cases` CRUD
- 상태 자동 계산 unit test

### M2. Dashboard frontend

목표:

- `/surgery` 화면 구현

산출물:

- 상단 summary cards
- 확인 필요 alert banner
- main table
- edit/create modal
- 우측 필수 보기
- 집도의별 요약

### M3. CSV import/export

목표:

- 엑셀/CSV 기반 운영 대응

산출물:

- CSV export
- CSV import
- sample CSV
- import validation

### M4. Cloud Run 배포

목표:

- 데모 가능한 URL 생성

산출물:

- Cloud Run service
- GCS bucket/prefix
- 인증 설정
- 배포 문서

### M5. Google Calendar sync

목표:

- 캘린더 생성/수정/취소 연동

산출물:

- Calendar API 연동
- event ID 저장
- sync error 표시
- manual sync button

---

## 16. 테스트 요구사항

### 16.1 상태 계산 테스트

필수 테스트 케이스:

1. 취소된 케이스는 취소
2. 오늘 수술은 진행중
3. 검사일이 없으면 확인필요
4. 검사일이 수술일 기준 8주 초과면 확인필요
5. 마취평가 미완료면 확인필요
6. 입원 여부 미정이면 확인필요
7. 동의서 미완료면 확인필요
8. 수술 전 설명 미완료면 확인필요
9. 금식 안내 미완료면 확인필요
10. 캘린더 미연동이면 확인필요
11. 캘린더 오류면 확인필요
12. 모든 필수 항목 완료 시 준비완료

### 16.2 API 테스트

- case 생성
- case 목록 조회
- case 상세 조회
- case 수정
- case 삭제
- cancel
- restore
- summary count
- alerts
- surgeon summary
- CSV export

### 16.3 Frontend 테스트

- summary card count가 API와 일치
- 확인필요 환자가 상단 노출
- 누락 항목 태그 표시
- 필터 클릭 시 table 갱신
- case 생성/수정 modal 동작
- 취소/복구 버튼 동작

---

## 17. MVP 완료 기준

MVP 완료 기준은 다음과 같다.

- `/surgery` 화면 접속 가능
- 수술 케이스 생성 가능
- 수술 케이스 수정 가능
- 수술 케이스 취소 가능
- 수술 케이스 목록이 GCS에 저장됨
- 이번 주 수술만 필터링 가능
- 확인필요 환자가 자동으로 상단 노출됨
- 누락 항목 태그가 표시됨
- summary card 5개가 정상 작동함
- 집도의별 수술 건수가 표시됨
- CSV export 가능
- 실제 환자정보 없이 sample data로 데모 가능

---

## 18. 교수님께 확인할 질문

개발 전 확인이 필요한 항목이다.

### 18.1 운영 범위

1. 실제 운영용인가, 데모/프로토타입인가?
2. 실제 환자정보를 넣을 예정인가?
3. 환자 실명 표시가 필요한가, 환자번호만으로 충분한가?
4. 사용자는 교수님 1명인가, 여러 명인가?
5. 코디네이터/간호사도 사용할 예정인가?

### 18.2 수술 정보

1. 수술명은 자유입력인가, 정해진 목록이 있는가?
2. 집도의 목록은 고정인가?
3. 수술방 목록은 고정인가?
4. 마취 종류는 어떤 값으로 나눌 것인가?
5. 입원 여부는 입원/당일/미정 정도면 충분한가?

### 18.3 준비 항목

1. 수술 2주 전까지 완료되어야 하는 항목은 무엇인가?
2. 검사 유효기간 8주 기준에 포함되는 검사는 무엇인가?
3. 동의서, 수술 전 설명, 금식 안내를 모두 필수로 볼 것인가?
4. 확인필요 기준에 캘린더 미연동을 포함할 것인가?

### 18.4 Calendar 연동

1. 실제 Google Calendar 연동이 필요한가?
2. 어떤 캘린더에 등록할 것인가?
3. 캘린더에 환자 코드를 표시해도 되는가?
4. 취소 시 event를 삭제할 것인가, `[취소]`로 남길 것인가?
5. 일정 변경 이력을 앱에 남겨야 하는가?

---

## 19. Codex 구현 지시 초안

```text
We are forking the existing jsbang01357/jisong_cloud project into a new GCS-backed surgery operations dashboard.

Goal:
Build a FastAPI + static frontend + Google Cloud Storage web app for managing weekly surgery schedules and preoperative preparation status.

Base architecture:
Keep the current api_server.py structure, static frontend serving, GCS helper utilities, authentication boundary, Docker/Cloud Run deployment style.
Add a new surgery module without breaking existing health/auth/frontend serving.

Implement:

1. Backend
- Add app/routers/surgery.py
- Add app/surgery_store.py
- Add app/surgery_status.py
- Add app/surgery_schema.py if helpful
- Store surgery cases as JSON blobs under GCS prefix surgery_ops/cases/
- Add audit log under surgery_ops/audit/surgery_ops_audit.jsonl

2. API endpoints
- GET /api/surgery/cases
- POST /api/surgery/cases
- GET /api/surgery/cases/{case_id}
- PUT /api/surgery/cases/{case_id}
- DELETE /api/surgery/cases/{case_id}
- GET /api/surgery/summary
- GET /api/surgery/alerts
- GET /api/surgery/surgeons/summary
- POST /api/surgery/cases/{case_id}/cancel
- POST /api/surgery/cases/{case_id}/restore
- GET /api/surgery/export.csv
- POST /api/surgery/import.csv

3. Status logic
Automatically compute status and missing_items on read:
- Cancelled cases -> 취소
- Today's surgery -> 진행중
- Surgery within 14 days with missing required prep -> 확인필요
- Missing lab date -> 확인필요
- Lab date older than 8 weeks before surgery date -> 확인필요
- Missing anesthesia evaluation, admission confirmation, consent, preop instruction, fasting instruction -> 확인필요
- Calendar status 미연동 or 오류 -> 확인필요
- Otherwise 준비완료

4. Frontend
- Add frontend/partials/surgery.html
- Add /surgery route to the existing frontend navigation
- Add dashboard cards: 전체, 준비완료, 확인필요, 진행중, 취소
- Add alert banner for 확인필요 cases
- Add main table sorted by 확인필요 first, then surgery date ascending
- Add surgeon summary panel
- Add create/edit case modal
- Add cancel/restore action
- Add CSV export button
- Add CSV import button if feasible

5. Data fields
Each surgery case should include:
case_id, patient_code, patient_name optional, surgery_date, surgery_start_time, surgery_end_time, surgery_name, surgeon, operating_room, anesthesia, admission_type, prep fields, calendar_status, calendar_event_id, is_cancelled, cancellation_reason, notes, created_at, updated_at.

6. Tests
Add Python unit tests for status calculation:
- cancelled
- today surgery
- missing lab date
- lab older than 8 weeks
- missing anesthesia evaluation
- all required items complete
- calendar error

Do not implement Google Calendar API yet.
Only keep calendar_status and calendar_event_id fields for later.
Do not store real patient data in tests or sample files.
```

---

## 20. 현재 결정사항

현재 기준 결정사항은 다음과 같다.

| 항목 | 결정 |
|---|---|
| 구현 방식 | Notion/Make가 아니라 GCS 기반 웹앱 |
| 기반 코드 | `jisong_cloud` fork/복제 |
| Backend | FastAPI |
| Frontend | 정적 HTML/CSS/JS |
| 저장소 | Google Cloud Storage JSON |
| 배포 | Cloud Run |
| Calendar 연동 | MVP에서는 상태값만, 2차에서 실제 API |
| 환자정보 | 실명 최소화, 환자코드 중심 |
| 상태 분류 | 조회 시 자동 계산 |
| MVP 핵심 | 확인필요 환자 자동 노출 |

---

## 21. 제외 범위

MVP에서 제외할 항목:

- 실제 Google Calendar API 연동
- 사용자별 세부 권한 관리
- 병원 EMR 연동
- 실시간 동시 편집
- 복잡한 audit diff view
- 모바일 전용 UI
- 고급 통계/리포트
- 실제 환자자료 기반 테스트
- Notion API 연동
- Make scenario 구현

---

## 22. 리스크

### 22.1 개인정보 리스크

실제 환자정보가 들어가면 보안/권한/로그 관리 기준이 높아진다.

대응:

- 실명 사용 최소화
- 별도 bucket 사용
- 접근 제한
- 테스트 데이터 분리
- GitHub commit 금지

### 22.2 요구사항 변경 리스크

수술 준비 항목과 상태 기준이 교수님/실무자에 따라 바뀔 수 있다.

대응:

- 상태 계산 로직 분리
- 필수 항목 설정화 가능성 고려
- 우선 MVP에서는 코드 상수로 구현

### 22.3 Calendar 연동 리스크

Calendar API 인증, 이벤트 수정/취소 정책, 개인정보 노출 문제가 생길 수 있다.

대응:

- MVP에서 제외
- event title에 환자 실명 금지
- event ID 저장
- sync error UI 표시

### 22.4 GCS JSON 확장성 리스크

케이스 수가 많아지면 GCS prefix scan 방식이 느려질 수 있다.

대응:

- 초기에는 문제 없음
- 추후 Firestore 또는 index JSON 도입 가능

---

## 23. 다음 액션

1. 새 repo 이름 결정
2. `jisong_cloud` 복제
3. 개인용 기능 숨김 또는 제거 범위 결정
4. `/api/surgery/*` backend 구현
5. `/surgery` frontend 구현
6. sample data 작성
7. 교수님 데모
8. 피드백 반영
9. Calendar API 2차 구현 여부 결정
