# 로컬 개발 및 검증 표준

이 문서는 Jisong Cloud 프로젝트의 로컬 개발 환경 설정과 코드 검증 표준을 정의합니다.

## 1. 개발 환경

### Python
- **버전**: Python 3.12 이상 권장
- **가상환경**: `.venv` 디렉토리를 사용합니다.
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### Node.js
- **버전**: Node 20 이상 권장 (v6 parser-core 및 JS 테스트 실행용)
- **설정**: `parser-core/` 디렉토리 내의 Node 패키지 의존성을 관리합니다.

---

## 2. 코드 검증 (Testing)

### Python 유닛 테스트
모든 백엔드 로직은 `unittest`를 기반으로 검증합니다.
- **실행 명령**:
  ```bash
  python3 -m unittest discover -s tests/python
  ```
- **표준**: 새로운 기능을 추가하거나 버그를 수정할 때 반드시 관련 테스트를 추가하거나 기존 테스트를 통과해야 합니다.

### JavaScript/Node 테스트
v6 파서 및 프론트엔드 관련 로직은 `tests/js` 아래의 스크립트로 검증합니다.
- **실행 예시**:
  ```bash
  node tests/js/run_emr_test.js
  ```

---

## 3. 서버 실행

### API 서버 (Starlette)
```bash
uvicorn api_server:app --host 127.0.0.1 --port 8080 --reload
```
- `--reload` 옵션은 개발 시 코드 변경사항을 즉시 반영하기 위해 사용합니다.
- 로컬 실행 시 Cloudflare Access 헤더가 없으므로 `REQUIRE_CLOUDFLARE_ACCESS=false` 환경을 기본으로 합니다.

---

## 4. 정적 분석 및 문법 검사
- **Python**: `py_compile`을 사용하여 기본적인 문법 오류를 체크합니다.
  ```bash
  python3 -m py_compile api_server.py app/*.py
  ```
- **JavaScript**: `node --check`를 사용하여 프론트엔드 JS 파일의 문법을 체크합니다.
  ```bash
  node --check frontend/app.js
  ```

---

## 5. 배포 전 체크리스트
- [ ] 전체 Python 테스트 통과 (`unittest`)
- [ ] v6 파서 관련 Node 스크립트 실행 확인
- [ ] API 서버 기동 및 프론트엔드 렌더링 확인
- [ ] `requirements.txt`에 신규 의존성 반영 여부 확인
- [ ] `cloudbuild.yaml` 환경변수가 운영 정책과 일치하는지 확인
