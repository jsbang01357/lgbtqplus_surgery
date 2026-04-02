import streamlit as st
import re
from custom_copy_btn import copy_to_clipboard


# --- 결과 출력 공통 함수 ---
def _render_result(clean_input, cleaned):
    """정리 결과를 화면에 출력합니다."""
    st.markdown("---")
    st.subheader("✨ 정리된 결과")

    orig_len = len(clean_input)
    clean_len = len(cleaned)
    removed = orig_len - clean_len
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("원본 글자수", f"{orig_len}자")
    with col_s2:
        st.metric("정리 후 글자수", f"{clean_len}자")
    with col_s3:
        st.metric("제거된 글자수", f"{removed}자")

    st.text_area("결과 (아래 버튼으로 복사 가능)", value=cleaned, height=250, key="clean_result_area")
    copy_to_clipboard(text=cleaned, before_copy_label="📋 결과 복사하기", after_copy_label="✅ 복사 완료", key="copy_clean_result")


# --- 일반 모드 ---
def _render_general_mode():
    """일반 텍스트 클리너 모드"""
    st.info("입력한 텍스트에서 불필요한 서식을 제거하고 깔끔하게 정리합니다.")

    st.markdown("**정리 옵션**")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        opt_tab = st.checkbox("탭 문자 제거", value=True)
        opt_multi_space = st.checkbox("연속 공백 → 단일 공백", value=True)
        opt_empty_lines = st.checkbox("연속 빈 줄 → 한 줄로", value=True)
        opt_trim_lines = st.checkbox("각 줄 앞뒤 공백 제거", value=True)
    with col_opt2:
        opt_line_numbers = st.checkbox("줄번호 제거 (예: 1. 또는 1) )", value=False)
        opt_urls = st.checkbox("URL 제거", value=False)
        opt_special_chars = st.checkbox("특수문자 제거 (글자/숫자/공백만 남김)", value=False)
        opt_merge_lines = st.checkbox("모든 줄바꿈 제거 (한 문단으로)", value=False)

    st.markdown("---")
    clean_input = st.text_area("정리할 텍스트를 입력하세요", height=250, placeholder="여기에 내용을 붙여넣으세요...")

    if st.button("깨끗하게 정리하기", type="primary", use_container_width=True):
        if clean_input:
            cleaned = clean_input

            if opt_tab:
                cleaned = cleaned.replace("\t", " ")
            if opt_trim_lines:
                cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
            if opt_multi_space:
                cleaned = "\n".join(
                    " ".join(line.split()) for line in cleaned.splitlines()
                )
            if opt_empty_lines:
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            if opt_line_numbers:
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned, flags=re.MULTILINE)
            if opt_urls:
                cleaned = re.sub(r'https?://\S+', '', cleaned)
            if opt_special_chars:
                cleaned = re.sub(r'[^\w\s가-힣]', '', cleaned)
            if opt_merge_lines:
                cleaned = " ".join(cleaned.splitlines())
                cleaned = " ".join(cleaned.split())

            cleaned = cleaned.strip()
            _render_result(clean_input, cleaned)
        else:
            st.warning("텍스트를 입력해주세요.")


# --- 1. 전각 스페이스 제거 ---

def _clean_emr_fullwidth_spaces(text, preserve_indent=False):
    """1. 전각 스페이스(U+3000, 　) 제거
    
    파이프라인 제일 앞에 위치해야 합니다.
    후속 기능(공백 정규화, 섹션 파싱 등)이 전부 여기에 의존합니다.
    
    Args:
        text: 원본 텍스트
        preserve_indent: True면 전각 공백을 4칸 공백으로 변환하여 
                         시각적 들여쓰기를 일부 유지. False면 1칸으로 치환.
    """
    if preserve_indent:
        return text.replace('\u3000', '    ')
    return text.replace('\u3000', ' ')


# --- 줄 분류기 (Line Classifier) ---
def _classify_line(line):
    """줄 유형을 분류합니다.
    
    Returns:
        'lab'       - 검사값 줄 (숫자 + 단위 + 화살표 등)
        'order'     - 처방/오더 줄 (날짜로 시작 + 여러 열)
        'narrative' - 일반 서술문 (현병력, S/O/A/P 텍스트 등)
        'empty'     - 빈 줄
        'header'    - 섹션 헤더 줄
    """
    stripped = line.strip()
    
    if not stripped:
        return 'empty'
    
    # 섹션 헤더: Problem>, S>, O>, A>, P(Care plan)> 등
    if re.match(r'^(Problem|S|O|A|P(?:\(.*?\))?|기본정보|진단정보|의뢰내용|회신내용|주호소|현병력|과거력|계획)\s*>?\s*$', stripped):
        return 'header'
    
    # Lab 줄 판별 기준:
    # - 숫자값 포함 + (단위 or 플래그(▲▼↑↓H L) or 참고범위(~))
    # - (응급), (혈액) 같은 prefix가 있는 경우
    has_number = bool(re.search(r'\d+\.?\d*', stripped))
    has_flag = bool(re.search(r'[▲▼↑↓★]|(?<!\w)[HL](?!\w)', stripped))
    has_unit = bool(re.search(r'(?:mg/d[lL]|mmol/L|mEq/L|g/d[lL]|%|U/L|μ?mol/L|pg/m[lL]|ng/m[lL]|cells/μ[lL]|mm/hr|×10)', stripped))
    has_ref_range = bool(re.search(r'~|–|−', stripped))
    has_lab_prefix = bool(re.match(r'^\s*\(.*?\)', stripped))
    
    # 주요 검사명 키워드 (대소문자 구분 및 단어 경계 활용하여 오탐 방지)
    lab_keywords = [
        'HbA1c', 'Glucose', 'BUN', 'Cr', 'GFR', 'Na', 'Cl',
        'Ca', 'Phos', 'I.Phos', 'Osmol', 'C-Peptide', 'WBC', 'Hb', 'Hgb',
        'Plt', 'PLT', 'AST', 'ALT', 'ALP', 'BNP', 'CRP', 'ESR', 'PCT',
        'Albumin', 'Protein', 'Bilirubin', 'LDH', 'CPK', 'Lipase',
        'Amylase', 'Troponin', 'D-dimer', 'Fibrinogen', 'PT', 'aPTT',
        'INR', 'Lactate', 'pH', 'pCO2', 'pO2', 'HCO3', 'BE',
        'VBGA', 'ABGA', 'Ketone', '베타케톤', 'FENa', 'FEUrea',
    ]
    # \b (단어 경계)를 사용하여 "Na중에" 등이 "Na"로 잡히는 것 방지
    has_lab_keyword = any(re.search(r'\b' + re.escape(kw) + r'\b', stripped) for kw in lab_keywords)
    
    # E' 패턴 (전해질 약어)
    if re.match(r"^\s*E'\s+[\d\-]+", stripped):
        return 'lab'
    
    # VBGA/ABGA 패턴
    if re.match(r'^\s*(V|A)BGA\s+[\d\.\-\s]+', stripped):
        return 'lab'
    
    # Lab 줄 종합 판정: 숫자가 있고, lab 관련 신호가 2개 이상이면 lab
    lab_signals = sum([has_flag, has_unit, has_ref_range, has_lab_prefix, has_lab_keyword])
    if has_number and lab_signals >= 1:
        return 'lab'
    
    # 오더 줄: 날짜(8자리)로 시작 + 뒤에 여러 열이 있는 경우
    if re.match(r'^\s*\d{4}[-/.]?\d{2}[-/.]?\d{2}', stripped):
        # 날짜 뒤에 공백으로 구분된 여러 필드가 있으면 order
        parts = stripped.split()
        if len(parts) >= 3:
            return 'order'
    
    return 'narrative'


def _normalize_spaces_for_line(line, line_type):
    """줄 타입에 따라 공백을 다르게 정규화합니다.
    
    - narrative: 연속 공백 2개 이상 → 1개
    - lab/order: 연속 공백 3개 이상 → 탭(구분자)
    - empty/header: 그대로 유지
    """
    if line_type == 'empty' or line_type == 'header':
        return line
    
    if line_type == 'narrative':
        # 줄 앞쪽의 들여쓰기는 보존하고, 본문 내 연속 공백만 축소
        leading = len(line) - len(line.lstrip(' '))
        indent = ' ' * min(leading, 1)  # 들여쓰기는 최대 1칸으로
        body = line.strip()
        body = re.sub(r' {2,}', ' ', body)  # 연속 공백 2+ → 1
        if not body:
            return ''
        return indent + body
    
    if line_type in ('lab', 'order'):
        # 줄 앞 공백은 탭 하나로 통일
        stripped = line.strip()
        if not stripped:
            return ''
        # 연속 공백 3개 이상 → 탭
        normalized = re.sub(r' {3,}', '\t', stripped)
        # 이미 있는 탭 + 공백 조합도 정리
        normalized = re.sub(r'\t +', '\t', normalized)
        normalized = re.sub(r' +\t', '\t', normalized)
        # 연속 탭 → 단일 탭
        normalized = re.sub(r'\t{2,}', '\t', normalized)
        return '\t' + normalized
    
    return line


def _clean_emr_normalize_spaces(text):
    """2. 연속 공백 정규화 (줄 타입별 분기 처리)
    
    줄마다 타입을 분류한 뒤:
    - narrative 줄: 연속 공백 2개 이상 → 1개로 축소
    - lab/order 줄: 연속 공백 3개 이상 → 탭(구분자)으로 변환
    - empty/header 줄: 그대로 유지
    """
    lines = text.splitlines()
    result = []
    
    for line in lines:
        line_type = _classify_line(line)
        normalized = _normalize_spaces_for_line(line, line_type)
        result.append(normalized)
    
    return "\n".join(result)



# --- 3. 기록 블록 분리 ---
# 기록 시작을 나타내는 패턴들 (문서 segmentation)
RECORD_STARTERS = [
    '타과회신', '타과의뢰', 
    'On Duty Note', 'Off Duty Note', 'Progress Note',
    '입원초진기록', '입원경과기록',
    '응급경과기록', '응급초진기록',
    '전문의기록', '전공의기록', '수련의기록',
    '퇴원요약', '수술기록', '시술기록',
    '간호기록', '영양상담기록',
]

def _clean_emr_block_separator(text):
    """3. 기록 블록 분리
    
    하나의 텍스트 안에 여러 기록(타과회신, On Duty Note, 입원초진기록 등)이 
    이어붙여져 있을 때, 각 기록의 경계를 시각적으로 분리합니다.
    
    record starter 패턴을 감지하여:
    - 구분선(===)을 삽입하고
    - 헤더 메타데이터(작성자, 확정/임시, 날짜)를 파싱하여 정리합니다.
    """
    # record starter를 regex OR 패턴으로 합침
    starters_pattern = '|'.join(re.escape(s) for s in RECORD_STARTERS)
    
    # 패턴: "기록유형  /작성자(상태)  [기록일:날짜]  날짜 시간 수정>날짜 시간"
    # 또는: "기록유형  /작성자(상태)  [기록일:날짜]  날짜 시간"
    record_header_pattern = re.compile(
        r'^(?P<type>' + starters_pattern + r')\s*/\s*'
        r'(?P<author>[^(]+)\((?P<status>[^)]+)\)\s*'
        r'\[기록일:\s*(?P<date>\S+)\]\s*'
        r'(?P<created>\S+\s+\S+)'
        r'(?:\s*수정>\s*(?P<modified>\S+\s+\S+))?'
    )
    
    # 처방 패턴: "이름 처방" 또는 "이름 처방 [기록일:...]"
    order_pattern = re.compile(
        r'^(?P<author>\S+)\s+처방\s*(?:\[기록일:\s*(?P<date>\S+)\])?\s*(?P<rest>.*)'
    )
    
    lines = text.splitlines()
    result = []
    is_first_block = True
    
    for line in lines:
        # 기록 헤더 패턴 매칭
        match = record_header_pattern.match(line.strip())
        if match:
            record_type = match.group('type')
            author = match.group('author').strip()
            status = match.group('status').strip()
            date = match.group('date').strip()
            created = match.group('created').strip()
            modified = match.group('modified')
            
            # 구분선 추가 (첫 블록 제외)
            if not is_first_block:
                result.append('')
            
            header = f"{'=' * 50}"
            result.append(header)
            
            meta = f"{record_type} | {author} | {status} | {date} {created}"
            if modified:
                meta += f" | 수정: {modified}"
            result.append(meta)
            result.append(header)
            
            is_first_block = False
            continue
        
        # 처방 패턴 매칭
        order_match = order_pattern.match(line.strip())
        if order_match and '처방' in line:
            author = order_match.group('author')
            date = order_match.group('date') or ''
            
            if not is_first_block:
                result.append('')
            
            header = f"{'=' * 50}"
            result.append(header)
            meta = f"처방 | {author}"
            if date:
                meta += f" | {date}"
            result.append(meta)
            result.append(header)
            
            is_first_block = False
            continue
        
        result.append(line)
    
    return "\n".join(result)


# --- 4. 섹션 헤더 표준화 ---
# canonical section name 매핑 딕셔너리
SECTION_CANONICAL_MAP = {
    # 기본 정보 계열
    '기본정보': '기본정보',
    '진단정보': '진단정보',
    '의뢰내용': '의뢰내용',
    '회신내용': '회신내용',
    
    # 병력 계열
    '주호소': '주호소',
    'CC': '주호소',
    '현병력': '현병력',
    'HPI': '현병력',
    '과거력': '과거력',
    'PMH': '과거력',
    '가족력': '가족력',
    'FHx': '가족력',
    '사회력': '사회력',
    'SHx': '사회력',
    '복용약물': '복용약물',
    
    # SOAP 계열
    'Problem': 'Problem',
    'S': 'S',
    'Subjective': 'S',
    'O': 'O',
    'Objective': 'O',
    'A': 'A',
    'Assessment': 'A',
    'P': 'Plan',
    'Plan': 'Plan',
    'P(Care plan)': 'Plan',
    'Care plan': 'Plan',
    '계획': 'Plan',
    
    # 신체검진
    '신체검진': '신체검진',
    'PE': '신체검진',
    'Physical Exam': '신체검진',
    'V/S': 'V/S',
    'Vital Signs': 'V/S',
    
    # 기타
    '검사소견': '검사소견',
    '영상소견': '영상소견',
    '경과': '경과',
}

def _clean_emr_section_headers(text):
    """4. 섹션 헤더 표준화
    
    EMR 내 섹션 헤더(Problem>, S>, O>, A>, P(Care plan)>, 기본정보> 등)를 
    canonical name으로 통일하고 형식을 정리합니다.
    
    매핑 예시:
    - P(Care plan)> → [Plan]
    - 계획> → [Plan]
    - 주호소> → [주호소]
    - S> → [S]
    """
    lines = text.splitlines()
    result = []
    
    # 섹션 헤더 후보 패턴:
    # "텍스트>" 또는 "텍스트(부가정보)>" 형태 (줄 전체가 헤더인 경우)
    section_pattern = re.compile(r'^\s*(.+?)\s*>\s*$')
    
    for line in lines:
        match = section_pattern.match(line)
        if match:
            raw_section = match.group(1).strip()
            
            # canonical name 찾기
            canonical = SECTION_CANONICAL_MAP.get(raw_section)
            
            if canonical:
                result.append(f"\n[{canonical}]")
                continue
            
            # 정확한 매치가 없으면 부분 매칭 시도
            # 예: "P(Care plan)" → key "P(Care plan)" → "Plan"
            found = False
            for key, value in SECTION_CANONICAL_MAP.items():
                if key in raw_section or raw_section in key:
                    result.append(f"\n[{value}]")
                    found = True
                    break
            
            if not found:
                # 매핑에 없는 섹션이라도 형식은 통일
                result.append(f"\n[{raw_section}]")
                continue
        else:
            result.append(line)
    
    return "\n".join(result)



def _clean_emr_empty_lines(text):
    """연속 빈 줄을 한 줄로 줄입니다."""
    return re.sub(r'\n{3,}', '\n\n', text)


# --- 5. Problem List Bullet화 ---
def _clean_emr_problem_list(text):
    """5. Problem List Bullet화
    
    #A., #B., #C. 같은 문자 태그 → Active Issues (현재 주요 문제)
    #1., #2., #3. 같은 숫자 태그 → PMH / Comorbidity (과거력/동반질환)
    
    변환 예:
        #A. DKA c newly-diagnosed DM
        #B. AKI
        #1. NSCLC
        #2. HTN
    →
        [Active Issues]
         - A. DKA c newly-diagnosed DM
         - B. AKI
        [Past History / Comorbidity]
         - 1. NSCLC
         - 2. HTN
    """
    lines = text.splitlines()
    result = []
    
    alpha_pattern = re.compile(r'^\s*#([A-Z])\.\s+(.+)')    # #A. ...
    num_pattern = re.compile(r'^\s*#(\d+)\.\s+(.+)')         # #1. ...
    sub_item_pattern = re.compile(r'^\s{2,}(.+)')             # 하위 항목 (들여쓰기)
    
    active_issues = []       # #A, #B, #C ...
    pmh_items = []           # #1, #2, #3 ...
    current_list = None      # 현재 수집 중인 리스트
    current_item_subs = []   # 현재 아이템의 하위 줄들
    
    def flush_lists():
        """수집된 리스트를 result에 출력"""
        nonlocal active_issues, pmh_items
        
        if active_issues:
            result.append("\t[Active Issues]")
            for item in active_issues:
                result.append(item)
            active_issues = []
        
        if pmh_items:
            result.append("\t[Past History / Comorbidity]")
            for item in pmh_items:
                result.append(item)
            pmh_items = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        alpha_match = alpha_pattern.match(line)
        num_match = num_pattern.match(line)
        
        if alpha_match:
            tag = alpha_match.group(1)
            content = alpha_match.group(2).strip()
            bullet_line = f"\t - {tag}. {content}"
            
            # 다음 줄이 하위 항목(들여쓰기)이면 같이 수집
            j = i + 1
            while j < len(lines):
                sub_match = sub_item_pattern.match(lines[j])
                # 다음 # 항목이 아니고 들여쓰기/탭으로 시작하는 줄이면 하위 항목
                if sub_match and not alpha_pattern.match(lines[j]) and not num_pattern.match(lines[j]):
                    bullet_line += "\n\t\t" + lines[j].strip()
                    j += 1
                else:
                    break
            
            active_issues.append(bullet_line)
            current_list = 'alpha'
            i = j
            continue
            
        elif num_match:
            tag = num_match.group(1)
            content = num_match.group(2).strip()
            bullet_line = f"\t - {tag}. {content}"
            
            j = i + 1
            while j < len(lines):
                sub_match = sub_item_pattern.match(lines[j])
                if sub_match and not alpha_pattern.match(lines[j]) and not num_pattern.match(lines[j]):
                    bullet_line += "\n\t\t" + lines[j].strip()
                    j += 1
                else:
                    break
            
            pmh_items.append(bullet_line)
            current_list = 'num'
            i = j
            continue
        
        else:
            # # 항목이 아닌 줄 → 수집 중인 리스트가 있으면 flush
            if active_issues or pmh_items:
                flush_lists()
                current_list = None
            result.append(line)
        
        i += 1
    
    # 마지막 남은 리스트 flush
    flush_lists()
    
    return "\n".join(result)


# --- 6. Lab 결과 줄 정렬 ---
# 플래그 문자를 읽기 쉬운 화살표로 변환
FLAG_MAP = {
    '▲': '↑', 'H': '↑', '△': '↑',
    '▼': '↓', 'L': '↓', '▽': '↓',
}

def _parse_lab_line(line):
    """Lab 줄을 5개 필드로 파싱합니다.
    
    Returns:
        dict with keys: test_name, value, flag, unit, ref_range
        또는 None (파싱 실패)
    """
    stripped = line.strip()
    if not stripped:
        return None
    
    # (응급) 또는 (혈액) 같은 prefix 제거 후 검사명에 포함
    prefix = ''
    prefix_match = re.match(r'^(\([^)]+\))\s*', stripped)
    if prefix_match:
        prefix = prefix_match.group(1)
        stripped = stripped[prefix_match.end():]
    
    # 패턴: 검사명 + 구분자(공백/탭) + 값 + [플래그] + [단위] + [참고범위]
    # 탭으로 이미 구분된 경우
    if '\t' in stripped:
        parts = [p.strip() for p in stripped.split('\t') if p.strip()]
    else:
        # 공백 기반 분리 (연속 공백 2+ 를 구분자로)
        parts = [p.strip() for p in re.split(r'\s{2,}', stripped) if p.strip()]
    
    if len(parts) < 2:
        return None
    
    test_name = prefix + parts[0]
    
    # 나머지 parts에서 value, flag, unit, ref_range 추출
    value = ''
    flag = ''
    unit = ''
    ref_range = ''
    
    remaining = parts[1:]
    
    for part in remaining:
        # 참고범위: ~ 포함
        if '~' in part or '–' in part or '−' in part:
            ref_range = part
        # 플래그: ▲, ▼, H, L (단독)
        elif part in ('▲', '▼', '△', '▽', 'H', 'L', '★'):
            flag = FLAG_MAP.get(part, part)
        # 단위: 알파벳/기호 조합 (숫자 없음)
        elif re.match(r'^[a-zA-Zμ%/×]+(?:[/\s][a-zA-Zμ]+)*$', part) and not re.search(r'\d', part):
            unit = part
        # 숫자값
        elif re.search(r'\d', part) and not value:
            value = part
        elif not value:
            value = part
        else:
            # 나머지는 참고범위에 추가
            if ref_range:
                ref_range += ' ' + part
            else:
                ref_range = part
    
    if not value:
        return None
    
    return {
        'test_name': test_name,
        'value': value,
        'flag': flag,
        'unit': unit,
        'ref_range': ref_range,
    }


def _clean_emr_lab_format(text, mode='compact'):
    """6. Lab 결과 줄 정렬
    
    Lab 줄(줄 분류기가 'lab'으로 판정한 줄)을 파싱하여 
    구조화된 형태로 변환합니다.
    
    Args:
        text: 원본 텍스트
        mode: 출력 형식
            'compact' - "HbA1c 10.8% ↑" (간결한 텍스트)
            'table'   - "| Test | Value | Unit | Flag | Ref |" (테이블)
    """
    lines = text.splitlines()
    result = []
    lab_buffer = []  # 연속 lab 줄을 모아두는 버퍼
    
    def flush_lab_buffer():
        """수집된 lab 줄들을 포맷팅하여 result에 추가"""
        nonlocal lab_buffer
        if not lab_buffer:
            return
        
        if mode == 'table' and len(lab_buffer) >= 1:
            result.append("\t| Test | Value | Unit | Flag | Ref |")
            result.append("\t|---|---:|---|---|---|")
            for parsed in lab_buffer:
                flag_str = parsed['flag'] if parsed['flag'] else ''
                unit_str = parsed['unit'] if parsed['unit'] else ''
                ref_str = parsed['ref_range'] if parsed['ref_range'] else ''
                result.append(f"\t| {parsed['test_name']} | {parsed['value']} | {unit_str} | {flag_str} | {ref_str} |")
        else:  # compact mode
            for parsed in lab_buffer:
                parts = [f"\t{parsed['test_name']}: {parsed['value']}"]
                if parsed['unit']:
                    parts[0] += f" {parsed['unit']}"
                if parsed['flag']:
                    parts[0] += f" {parsed['flag']}"
                if parsed['ref_range']:
                    parts[0] += f" (ref {parsed['ref_range']})"
                result.append(parts[0])
        
        lab_buffer = []
    
    for line in lines:
        line_type = _classify_line(line)
        
        if line_type == 'lab':
            parsed = _parse_lab_line(line)
            if parsed:
                lab_buffer.append(parsed)
            else:
                # 파싱 실패 시 원본 유지
                flush_lab_buffer()
                result.append(line)
        else:
            # lab이 아닌 줄을 만나면 버퍼 flush
            flush_lab_buffer()
            result.append(line)
    
    # 마지막 남은 lab 버퍼
    flush_lab_buffer()
    
    return "\n".join(result)


def _clean_emr_special_markers(text):
    """EMR 특수 마커(★, ▲, △ 등)를 제거합니다."""
    return re.sub(r'[★▲△▼▽●○◆◇■□]', '', text)


def _render_emr_mode():
    """KUMC EMR 모드"""
    st.info("KUMC EMR 텍스트를 깔끔하게 정리합니다. On Duty Note, Progress Note 등을 붙여넣으세요.")

    st.markdown("**정리 옵션**")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.caption("전처리")
        emr_fullwidth = st.checkbox("전각 스페이스(　) 제거", value=True, key="emr_fw")
        emr_preserve_indent = st.checkbox("┗ 들여쓰기 시각적 유지 (4칸 변환)", value=False, key="emr_pi")
        emr_normalize = st.checkbox("연속 공백 정규화 (줄 타입별 자동 분기)", value=True, key="emr_norm")
        emr_empty = st.checkbox("연속 빈 줄 → 한 줄로", value=True, key="emr_empty")
    with col_opt2:
        st.caption("구조 정리")
        emr_block = st.checkbox("기록 블록 분리 (구분선 삽입)", value=True, key="emr_block")
        emr_section = st.checkbox("섹션 헤더 표준화 (canonical name)", value=True, key="emr_sec")
        emr_problem = st.checkbox("Problem List Bullet화", value=True, key="emr_prob")
        emr_lab = st.checkbox("Lab 결과 줄 정렬", value=True, key="emr_lab")
        emr_markers = st.checkbox("특수 마커 제거 (★, ▲ 등)", value=False, key="emr_markers")
    
    # Lab 출력 형식 선택 (Lab 옵션이 켜져 있을 때만 표시)
    lab_mode = 'compact'
    if emr_lab:
        lab_mode = st.radio(
            "Lab 출력 형식",
            ['compact', 'table'],
            format_func=lambda x: '📝 Compact (HbA1c: 10.8% ↑)' if x == 'compact' else '📊 Table (| Test | Value | ... |)',
            horizontal=True,
            key="emr_lab_mode"
        )

    st.markdown("---")
    emr_input = st.text_area(
        "EMR 텍스트를 입력하세요",
        height=300,
        placeholder="On Duty Note 또는 Progress Note를 여기에 붙여넣으세요...",
        key="emr_input"
    )

    if st.button("EMR 정리하기", type="primary", use_container_width=True, key="emr_btn"):
        if emr_input:
            cleaned = emr_input

            # === 파이프라인 순서 ===
            
            # 1단계: 전각 공백 제거
            if emr_fullwidth:
                cleaned = _clean_emr_fullwidth_spaces(cleaned, preserve_indent=emr_preserve_indent)
            
            # 2단계: 연속 공백 정규화
            if emr_normalize:
                cleaned = _clean_emr_normalize_spaces(cleaned)
            
            # 3단계: 기록 블록 분리
            if emr_block:
                cleaned = _clean_emr_block_separator(cleaned)
            
            # 4단계: 섹션 헤더 표준화
            if emr_section:
                cleaned = _clean_emr_section_headers(cleaned)
            
            # 5단계: Problem List Bullet화
            if emr_problem:
                cleaned = _clean_emr_problem_list(cleaned)
            
            # 6단계: Lab 결과 정렬
            if emr_lab:
                cleaned = _clean_emr_lab_format(cleaned, mode=lab_mode)
            
            # 기타: 빈 줄 정리, 특수 마커
            if emr_empty:
                cleaned = _clean_emr_empty_lines(cleaned)
            if emr_markers:
                cleaned = _clean_emr_special_markers(cleaned)

            cleaned = cleaned.strip()
            _render_result(emr_input, cleaned)
        else:
            st.warning("EMR 텍스트를 입력해주세요.")



# --- 메인 렌더 함수 ---
def render_text_cleaner():
    """텍스트 클리너 페이지를 렌더링합니다."""
    st.title("🧹 텍스트 클리너")

    mode = st.radio(
        "모드 선택",
        ["📝 일반 모드", "🏥 KUMC EMR 모드"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("---")

    if mode == "📝 일반 모드":
        _render_general_mode()
    elif mode == "🏥 KUMC EMR 모드":
        _render_emr_mode()
