좋습니다. 오늘은 **“맥미니 로컬 서버 설치 + 내부망 접속 + 계정 발급 + 기존 데이터 이관 + 교수님 사용 시작”**까지 끝내는 날로 잡으면 됩니다.

핵심은 이겁니다.

오늘 목표는 완성형 센터 EMR이 아니라,
외래 내부망에서 교수님들이 실제 수술계획을 입력·조회·수정할 수 있는 1차 운영 환경을 여는 것입니다.

현재 레포는 이미 auth, surgery router가 붙은 Qplus Surgery API 구조이고, 수술 데이터 CRUD/summary/import/export가 구현되어 있습니다.
수술 데이터는 GCS의 surgery_ops/cases에 저장되고 audit log도 남는 구조입니다.

⸻

오늘 해야 할 일 전체 순서

0. 시작 전 10분: 오늘 범위 선언

교수님께 먼저 이렇게 말하고 시작하세요.

교수님, 오늘은 외래 맥미니를 로컬 서버로 설치해서 내부망에서 접속 가능한 1차 운영 환경을 열어두겠습니다.
오늘 목표는 수술계획 등록, 조회, 수정, 취소, CSV 기반 기존 데이터 이관까지입니다.
센터 EMR 전체 기능과 AI 요약 기능은 다음 단계로 확장하고, 오늘은 실제 업무가 가능한 최소 운영 버전을 안정적으로 세팅하겠습니다.

이 말을 먼저 해두면 “왜 AI 요약은 아직 안 돼?” 같은 기대치를 조절할 수 있습니다.

⸻

1. 맥미니 물리 설치

해야 할 일

[ ] 맥미니 외래에 설치
[ ] 전원 연결
[ ] 가능하면 유선 LAN 연결
[ ] Wi-Fi는 보조망으로만 연결
[ ] 모니터/키보드 없이도 원격 관리 가능하게 설정
[ ] macOS 자동 잠자기 해제
[ ] 맥미니 이름 설정: qplus-surgery

중요

병원 내부망과 외부 Wi-Fi를 동시에 붙이더라도 인터넷 공유/브리지 기능은 켜면 안 됩니다.
맥미니가 병원망과 외부망을 이어주는 장비처럼 보이면 보안 문제가 됩니다.

⸻

2. 네트워크 접속 확인

맥미니에서 내부망 IP 확인

ipconfig getifaddr en0

또는 Wi-Fi면:

ipconfig getifaddr en1

예시:

192.168.0.35

교수님/외래 PC 접속 주소

중요합니다.

교수님 PC에서 localhost가 아닙니다.
localhost는 각자 자기 컴퓨터입니다.

교수님 PC에서는 이렇게 접속해야 합니다.

http://맥미니IP:8080

예시:

http://192.168.0.35:8080

체크

[ ] 맥미니에서 http://127.0.0.1:8080 접속
[ ] 교수님 PC에서 http://맥미니IP:8080 접속
[ ] 코디/외래 PC에서도 접속
[ ] 모바일 병원 Wi-Fi에서도 필요한 경우 접속 확인

⸻

3. 레포 준비

현재 lgbtqplus_surgery 레포는 public 상태로 확인됩니다. 실제 운영 전에는 private 전환이 필요합니다.  

맥미니에서 코드 받기

cd ~/Developer
git clone https://github.com/jsbang01357/lgbtqplus_surgery.git
cd lgbtqplus_surgery

이미 있으면:

cd ~/Developer/lgbtqplus_surgery
git pull

Python 환경 세팅

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

requirements.txt에는 FastAPI, uvicorn, GCS, Google Calendar API 관련 패키지가 포함되어 있습니다.

⸻

4. 오늘 반드시 해야 하는 보안 조치

4-1. GitHub repo private 전환

[ ] GitHub repo public → private

이건 오늘 1순위입니다.
실제 환자정보가 들어가지 않아도, 수술 운영 구조와 인증 구조가 노출되는 건 좋지 않습니다.

⸻

4-2. 공개 회원가입 차단

현재 /api/auth/account/register가 있고, email/password를 받아서 GCS의 auth/users.json에 저장하는 구조입니다.
오늘 실제 운영을 열 거면 공개 회원가입은 막아야 합니다.

오늘 처리 기준

[ ] /api/auth/account/register 비활성화
[ ] 또는 admin-only로 제한
[ ] 또는 ALLOW_PUBLIC_REGISTRATION=false 환경변수로 차단

급하면 가장 단순하게:

register endpoint는 403 반환
계정은 지송이 직접 생성

⸻

4-3. Google Calendar에 환자명 제거

현재 Calendar sync는 환자명/선호이름을 event summary와 description에 넣을 수 있습니다.
오늘 실제 데이터 넣기 전에 고쳐야 합니다.

변경 원칙

Calendar 제목:

[확정] P-0001 / 수술명 / 집도의

Calendar 설명:

환자코드:
수술명:
집도의:
수술방:
마취:
준비상태:
누락항목:

Calendar에는 넣지 말 것:

환자명
선호이름
진단명
상세 비고
민감한 수술 전 정보

⸻

5. 환경변수 설정

오늘 GCS 저장 구조를 그대로 쓴다면 환경변수부터 잡아야 합니다.

export GCS_BUCKET_NAME="lgbtqplus-surgery"
export REQUIRE_CLOUDFLARE_ACCESS="false"
export ALLOW_ACCOUNT_ID_FALLBACK="true"
export JISONG_ACCOUNT_LOGIN_ID="관리자이메일"
export ADMIN_PASSWORD="초기관리자비밀번호"
export PASSKEY_RP_ID="맥미니IP"
export PASSKEY_ORIGIN="http://맥미니IP:8080"
export PASSKEY_RP_NAME="Qplus Surgery"

예시:

export PASSKEY_RP_ID="192.168.0.35"
export PASSKEY_ORIGIN="http://192.168.0.35:8080"

오늘 passkey까지 안 쓸 거면 계정 ID/password fallback 중심으로 가면 됩니다.

⸻

6. 서버 실행

개발 실행

source .venv/bin/activate
uvicorn api_server:app --host 0.0.0.0 --port 8080

--host 0.0.0.0이 중요합니다.
127.0.0.1로 띄우면 맥미니 본인만 접속됩니다.

확인

[ ] 맥미니: http://127.0.0.1:8080
[ ] 외래 PC: http://맥미니IP:8080
[ ] 로그인 화면 확인
[ ] 수술 대시보드 화면 확인

⸻

7. 서버 자동 실행 설정

오늘 현장에서 계속 터미널 켜놓을 수는 있지만, 가능하면 자동 실행까지 해두는 게 좋습니다.

최소 운영안

터미널 하나 열어놓고 uvicorn 실행 유지
화면 잠금은 가능
맥미니 잠자기 금지

더 나은 운영안

launchd로 자동 실행 등록.

오늘 시간이 부족하면 자동 실행은 내일 해도 됩니다.
오늘은 우선 “서버가 꺼지지 않는 것”이 중요합니다.

[ ] 맥미니 잠자기 방지
[ ] 터미널 실행 유지
[ ] 재부팅 시 복구 방법 메모

⸻

8. 계정 10개 생성

현재 로그인은 등록된 사용자 비밀번호 해시를 확인하고, 성공하면 account session cookie를 발급하는 구조입니다.
세션은 GCS의 auth/account_sessions.json에 저장됩니다.

사용자 명단 만들기

[ ] 이름
[ ] 이메일
[ ] 역할
[ ] 초기 비밀번호
[ ] 사용 여부
[ ] 비고

역할은 오늘은 간단히

admin: 지송, 교수님
staff: 코디/실무자
viewer: 보기 전용, 추후 구현

현재 role-based permission이 완전히 붙어 있지 않으면, 오늘은 role을 metadata로만 남겨도 됩니다.

오늘 계정 운영 원칙

[ ] 공개 회원가입 X
[ ] 지송이 사전 생성
[ ] 초기 비밀번호 개별 전달
[ ] 계정/비밀번호는 카톡방 전체 공유 금지
[ ] 테스트 계정 1개로 먼저 로그인 확인
[ ] 교수님 계정 로그인 확인

⸻

9. 수술계획 기능 테스트

현재 /api/surgery/cases, summary, alerts, surgeons summary, cancel/restore, CSV export/import가 구현되어 있습니다.

기능 테스트 순서

[ ] 신규 수술 1건 등록
[ ] 수술일/시간 수정
[ ] 집도의 수정
[ ] 수술방 수정
[ ] 준비상태 변경
[ ] 확인필요 항목 표시 확인
[ ] 취소 처리
[ ] 복구 처리
[ ] 삭제 테스트
[ ] CSV export
[ ] CSV import

상태 계산 확인

현재 상태 계산은 취소, 오늘 수술, 검사일 누락, 8주 초과, 캘린더 오류, 14일 이내 준비항목 미완료 기준으로 돌아갑니다.

테스트 케이스:

[ ] 검사일 없는 환자 → 확인필요
[ ] 검사일 8주 초과 → 확인필요
[ ] 프리메드 미완료 → 확인필요
[ ] 서류확인 미완료 → 확인필요
[ ] 오늘 수술 → 진행중
[ ] 취소 환자 → 취소
[ ] 모든 항목 완료 → 준비완료

⸻

10. 기존 데이터 이관

오늘 제일 중요한 작업입니다.

10-1. 원본 백업

[ ] 기존 수술계획 원본 파일 받기
[ ] 원본 파일 복사본 만들기
[ ] 원본은 절대 직접 수정하지 않기
[ ] backup/original_YYYYMMDD 폴더에 보관

10-2. 이관용 CSV 만들기

필수 컬럼:

patient_code
surgery_date
surgery_name
surgeon

권장 컬럼:

patient_name
patient_preferred_name
surgery_start_time
surgery_end_time
operating_room
anesthesia
admission_type
diagnosis
room_type
surgery_status
notes

현재 import는 한글 컬럼명도 매핑합니다. 예를 들어 등록번호, 환자명, 수술일자, 수술명, 집도의, 수술실, 마취방법, 입원구분, 검사일자, 비고 등이 매핑됩니다.

10-3. 샘플 5건 import

전체 넣기 전에 반드시 5건만 먼저 넣으세요.

[ ] 샘플 5건 import
[ ] 화면에서 날짜 확인
[ ] 환자코드 확인
[ ] 이름 표시 여부 확인
[ ] 수술명 확인
[ ] 집도의별 요약 확인
[ ] 확인필요 항목 확인
[ ] CSV export해서 원본과 비교

10-4. 전체 import

샘플 검증 후 전체 이관.

[ ] 전체 CSV import
[ ] 총 건수 확인
[ ] 날짜 누락 확인
[ ] 환자코드 중복 확인
[ ] 취소 환자 분류 확인
[ ] 집도의별 건수 확인
[ ] 확인필요 환자 수 확인
[ ] export.csv로 다시 내려받아 원본과 비교

⸻

11. 교수님 사용 환경 세팅

교수님께 바로 드릴 정보

접속 주소:
http://맥미니IP:8080
계정:
[교수님 이메일]
초기 비밀번호:
[개별 전달]
오늘 가능한 기능:
1. 수술 일정 조회
2. 신규 수술 등록
3. 수술 일정 수정
4. 수술 취소/복구
5. 확인필요 항목 확인
6. 집도의별 수술 현황 확인
7. CSV 가져오기/내보내기

현장에서 설명할 말

교수님, 오늘은 외래 내부망에서 바로 접속 가능한 1차 운영 버전입니다.
기존 수술계획 데이터를 CSV로 이관해두고, 이후부터는 이 화면에서 신규 등록·수정·취소가 가능하게 해두겠습니다.
사용하시다가 항목명이 안 맞거나, 기존 workflow와 다른 부분이 있으면 말씀해주시면 바로 수정하겠습니다.

⸻

12. 코디/실무자에게 안내

오늘부터 수술계획 대시보드를 1차 테스트로 열어두겠습니다.
접속은 외래 내부망에서 맥미니 서버 주소로 들어가는 방식입니다.
계정은 제가 만들어드릴 예정이고, 로그인 후 수술 일정 조회, 신규 등록, 수정, 취소, 엑셀 가져오기/내보내기가 가능합니다.
처음부터 완성본으로 쓰는 단계라기보다는, 기존 업무 흐름과 화면 구조가 맞는지 확인하는 단계로 봐주시면 됩니다.
항목명이 헷갈리거나, 빠진 항목이 있거나, 기존 엑셀과 안 맞는 부분이 있으면 바로 말씀해주세요.

⸻

13. 오늘 끝나기 전 백업

운영 시작한 날에는 무조건 백업을 남겨야 합니다.

[ ] import 전 원본 CSV 백업
[ ] import 후 export.csv 다운로드
[ ] export.csv를 날짜 붙여 저장
[ ] GCS bucket에 데이터 저장 확인
[ ] audit log 생성 확인
[ ] 계정 목록 백업
[ ] 오늘 변경사항 git commit

단, 실제 환자정보가 들어간 CSV는 GitHub에 올리면 안 됩니다.

⸻

14. 오늘 하지 말아야 할 것

[ ] 실제 환자정보 들어간 CSV를 GitHub에 올리기
[ ] repo public 상태로 운영 시작하기
[ ] 공개 회원가입 열어두기
[ ] Google Calendar에 환자명 넣기
[ ] 맥미니를 병원망-외부망 bridge처럼 쓰기
[ ] 원본 엑셀을 백업 없이 수정하기
[ ] 전체 import 후 검증 없이 완료 처리하기
[ ] AI 요약 기능까지 오늘 무리하게 붙이기
[ ] 센터 EMR 전체를 오늘 완성하겠다고 말하기

⸻

오늘의 시간표

1시간차: 서버 설치

[ ] 맥미니 설치
[ ] 내부망 IP 확인
[ ] repo pull
[ ] venv 세팅
[ ] 서버 실행
[ ] 외래 PC 접속 확인

2시간차: 보안 잠금

[ ] repo private
[ ] 공개 register 차단
[ ] Calendar 실명 제거
[ ] 관리자 로그인 확인
[ ] 테스트 계정 로그인 확인

3시간차: 기능 검증

[ ] 수술 등록
[ ] 수정
[ ] 취소
[ ] 복구
[ ] CSV export
[ ] CSV import
[ ] 확인필요 표시

4시간차: 데이터 이관

[ ] 원본 백업
[ ] CSV 컬럼 정리
[ ] 샘플 5건 import
[ ] 검증
[ ] 전체 import
[ ] export로 재검증

마지막 30분: 인계

[ ] 교수님 접속 주소 전달
[ ] 계정 전달
[ ] 사용 가능 기능 설명
[ ] 제한사항 설명
[ ] 오류 제보 방식 안내
[ ] 내일 할 일 정리

⸻

오늘의 완료 기준

오늘 성공 기준은 이겁니다.

[ ] 외래 내부망 PC에서 접속된다.
[ ] 교수님 계정으로 로그인된다.
[ ] 수술계획을 등록할 수 있다.
[ ] 수술계획을 수정할 수 있다.
[ ] 수술계획을 취소/복구할 수 있다.
[ ] 기존 데이터가 일부 또는 전체 이관된다.
[ ] 확인필요 환자가 자동으로 뜬다.
[ ] CSV export가 된다.
[ ] 교수님이 직접 화면을 보고 “이걸로 시작할 수 있겠다”고 느낀다.

⸻

내일 이후로 넘길 일

오늘 하지 말고 내일 이후로 넘기면 되는 것들입니다.

[ ] AI 요약 기능
[ ] 센터 EMR 전체 환자 타임라인
[ ] GAHT 모듈
[ ] 연구 dataset builder
[ ] role-based permission 고도화
[ ] 비밀번호 변경 UI
[ ] 자동 백업 스케줄
[ ] launchd 서비스 정식 등록
[ ] Cloudflare Access
[ ] 병원 EMR export 자동 파이프라인

오늘은 서버 열기, 계정 만들기, 데이터 넣기, 교수님이 쓰게 하기만 하면 됩니다.
이 네 개가 끝나면 오늘은 충분히 이긴 겁니다.