import json
import os
import sys
import re
import argparse

from config import contracts

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================
# prohibitions.md 파싱 — §2 + §3에서 금지 패턴을 런타임 추출
# 하드코딩 대신 파일 파싱으로 파이프라인 범용성 보장
#
# 파싱 전략:
#   1. §2 (Narrative Stance) — "Banned Pattern / Example" 열에서 따옴표 내 문구 추출
#   2. §3 (Banned Word & Phrase) — "Banned Examples / Patterns" 열에서 따옴표 내 문구 추출
#   3. 두 섹션 모두 2번째 파이프 열(index=2)에서 따옴표 패턴 사용
#   4. 테이블 헤더행과 구분선은 건너뜀
# ============================================================
def parse_prohibitions():
    """prohibitions.md의 §2, §3 테이블에서 금지 패턴을 추출"""
    banned_phrases = []
    path = '.agents/rules/prohibitions.md'
    if not os.path.exists(path):
        return banned_phrases

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 테이블 행 추출 — 파이프 구분자가 있는 행만 대상
    for line in content.split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue

        # 헤더/구분선 건너뜀 — 정규식으로 다양한 구분선 포맷 대응
        if line.startswith('| Category') or re.match(r'^\|[\s\-:|]+\|', line):
            continue

        parts = line.split('|')
        if len(parts) < 3:
            continue

        # 2번째 열 (Banned Pattern / Example 또는 Banned Examples / Patterns)
        examples_col = parts[2].strip()

        # 따옴표로 감싼 구문 추출
        quoted = re.findall(r'"([^"]+)"', examples_col)

        # 따옴표가 없으면 쉼표로 구분된 항목 추출 (예: "Moving on to", "Next", ...)
        if not quoted:
            # 마크다운 이탤릭/볼드 제거 후 쉼표 분리
            cleaned = re.sub(r'[*_]', '', examples_col)
            items = [i.strip() for i in cleaned.split(',') if i.strip()]
            for item in items:
                # 너무 긴 설명문은 건너뜀 (실제 금지어가 아닌 설명)
                if len(item) > 60:
                    continue
                banned_phrases.append(item.lower())
        else:
            banned_phrases.extend([q.lower() for q in quoted])

    # 중복 제거
    banned_phrases = list(set(banned_phrases))

    # 파싱 실패 시 안전장치 — 핵심 AI 금지어만 하드코딩
    if not banned_phrases:
        banned_phrases = [
            "game-changer", "revolutionary", "delve", "dive deep",
            "testament", "unveil", "best overall", "the clear winner",
            "one buyer said", "a reviewer noted", "one user mentioned",
            "moving on to", "furthermore", "strip away",
            "many users", "some buyers", "a lot of", "most people",
            "i analyzed", "i found", "i read", "my data shows", "let's look at",
            "it's important to note", "needless to say",
            "at the end of the day", "picture this",
            "crime scene", "damning evidence", "indictment", "prosecution"
        ]

    return banned_phrases

# ============================================================
# 공통 유틸: theme_name -> category_pattern_type 매핑 구축
# CHECK 2, 6에서 공유
# ============================================================
def build_theme_pattern_map(tone_data):
    """tone_data에서 theme_name -> category_pattern_type 매핑 생성"""
    theme_patterns = {}
    for t in tone_data.get('common_themes', []):
        theme_patterns[t['theme_name']] = t.get('category_pattern_type', 'differentiator')
    return theme_patterns

# [CHECK 0 — BGM Mood Assignment 제거됨]
# bgm_mood 필드는 directing_hint로 흡수 (architecture_update_plan_v3 Phase 1-1)
# Creative Director가 directing_hint 작성 시 톤 방향을 자체 판단

# ============================================================
# CHECK 2 — Tension/Climax Order (블록 순서 검증)
# template별 기대 suffix 순서와 실제 블록 순서를 비교하여
# 순서 위반(tension escalation 불일치)을 감지
# ============================================================

# pacing_profiles.md §6 기반 — pipeline_contracts.json에서 로드
EXPECTED_SUFFIX_ORDER = contracts()["block_structure"]["expected_suffix_order"]

def check_2_tension_climax(outline, tone_data):
    """scene 내 블록 순서가 template별 기대 순서를 따르는지 검증"""
    flags = []
    theme_patterns = build_theme_pattern_map(tone_data)

    for scene in outline.get('scenes', []):
        if scene.get('scene_type') != 'metric_chapter':
            continue

        scene_id = scene.get('scene_id', '')
        themes = scene.get('assigned_themes', [])
        if not themes:
            continue

        theme_name = themes[0]
        pattern = theme_patterns.get(theme_name, 'differentiator')
        expected = EXPECTED_SUFFIX_ORDER.get(pattern, [])

        if not expected or len(expected) <= 1:
            continue

        # outline의 block_ids에서 suffix 추출 후 기대 순서와 비교
        block_ids = scene.get('block_ids', [])
        actual_suffixes = []
        for bid in block_ids:
            for suffix in expected:
                if bid.endswith(f"_{suffix}"):
                    actual_suffixes.append(suffix)
                    break

        # 순서 검증: suffix 인덱스가 단조 증가해야 함
        if len(actual_suffixes) > 1:
            expected_indices = [expected.index(s) for s in actual_suffixes]
            for i in range(1, len(expected_indices)):
                if expected_indices[i] <= expected_indices[i - 1]:
                    flags.append({
                        "check": "CHECK 2",
                        "block_id": scene_id,
                        "severity": "error",
                        "original": f"Block order: {actual_suffixes}",
                        "suggestion": f"'{pattern}' template expects order {expected}. Actual: {actual_suffixes}",
                        "auto_fixed": False
                    })
                    break

    # climax 후보 감지 (info 수준 — Creative Director 참고용)
    for t in tone_data.get('common_themes', []):
        if t.get('category_pattern_type') == 'differentiator':
            pairs = t.get('contradiction_pairs', [])
            if len(pairs) > 0:
                flags.append({
                    "check": "CHECK 2",
                    "block_id": f"theme_{t['theme_name'].lower().replace(' ', '_')[:15]}",
                    "severity": "info",
                    "original": "",
                    "suggestion": f"Climax candidate: '{t['theme_name']}' has {len(pairs)} contradiction pairs.",
                    "auto_fixed": False
                })

    return flags

# ============================================================
# CHECK 3 — AI Trace Scan (금지어 패턴 매칭)
# prohibitions.md에서 파싱한 금지어를 narration에서 검출
#
# 매칭 전략:
#   - 2단어 이상 구문: 정확히 해당 구문이 나레이션에 포함되는지 확인
#   - 1단어: word boundary(\b)로 독립 단어 매칭
#   - 대소문자 무시
# ============================================================
def check_3_ai_trace_scan(draft, banned_phrases):
    """narration 텍스트에서 금지 패턴 감지"""
    flags = []
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            text = block.get('narration', '')
            text_lower = text.lower()
            b_id = block.get('block_id')

            for phrase in banned_phrases:
                # 구문 길이에 따른 매칭 전략 분기
                if ' ' in phrase:
                    # 다단어 구문: 부분 문자열 매칭 (word boundary 불필요)
                    if phrase in text_lower:
                        flags.append({
                            "check": "CHECK 3",
                            "block_id": b_id,
                            "severity": "error",
                            "original": text[:200] + ("..." if len(text) > 200 else ""),
                            "suggestion": f"Remove banned phrase: '{phrase}'",
                            "auto_fixed": False
                        })
                else:
                    # 단일 단어: word boundary로 독립 매칭
                    if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
                        flags.append({
                            "check": "CHECK 3",
                            "block_id": b_id,
                            "severity": "error",
                            "original": text[:200] + ("..." if len(text) > 200 else ""),
                            "suggestion": f"Remove banned word: '{phrase}'",
                            "auto_fixed": False
                        })
    return flags

# [CHECK 5 — Tone Weight Balance 제거됨]
# bgm_mood 기반 산술이므로 CHECK 0 제거와 함께 자동 해소

# ============================================================
# CHECK 6 — Scene Balance (pattern_type별 블록 수 허용 범위 검증)
# pacing_profiles.md §4 + §6 기반 범위 테이블 참조
# ============================================================

# pattern_type별 허용 블록 수 범위 — pipeline_contracts.json에서 로드
_block_ranges_raw = contracts()["block_structure"]["block_range_by_pattern"]
BLOCK_RANGE_BY_PATTERN = {k: tuple(v) for k, v in _block_ranges_raw.items()}

def check_6_scene_balance(outline, tone_data):
    """theme별 블록 수가 pattern_type 허용 범위 내인지 검증"""
    flags = []
    theme_patterns = build_theme_pattern_map(tone_data)

    for scene in outline.get('scenes', []):
        if scene.get('scene_type') != 'metric_chapter':
            continue

        scene_id = scene.get('scene_id', '')
        block_ids = scene.get('block_ids', [])
        block_count = len(block_ids)

        # scene의 assigned_themes에서 pattern_type 조회
        themes = scene.get('assigned_themes', [])
        theme_name = themes[0] if themes else None
        pattern = theme_patterns.get(theme_name, 'differentiator') if theme_name else 'differentiator'

        min_blocks, max_blocks = BLOCK_RANGE_BY_PATTERN.get(pattern, (1, 4))

        if block_count < min_blocks or block_count > max_blocks:
            flags.append({
                "check": "CHECK 6",
                "block_id": scene_id,
                "severity": "warning",
                "original": f"{block_count} blocks (pattern: {pattern})",
                "suggestion": f"'{pattern}' template allows {min_blocks}-{max_blocks} blocks. Found {block_count}.",
                "auto_fixed": False
            })

    return flags

# ============================================================
# CHECK 9 — Data Anchoring (evidence 유무 + 면제 구역 검사)
# evidence_quotes가 빈 블록에서 제품 특정 주장이 있는지 감지
# Hook Stage 1, recommendation_outro는 면제 처리
# ============================================================

# 면제 블록 ID 목록 — pipeline_contracts.json에서 로드
EXEMPT_BLOCK_IDS = set(contracts()["merge"]["exempt_block_ids"])

def check_9_data_anchoring(draft, outline):
    """evidence가 없는 블록에서 실질적 narration이 있으면 플래그"""
    flags = []
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            b_id = block.get('block_id', '')
            narration = block.get('narration', '')
            quotes = block.get('evidence_quotes', [])

            # 면제 구역 건너뜀
            if b_id in EXEMPT_BLOCK_IDS:
                continue

            # evidence_quotes가 비어있고 narration에 실질적 내용이 있으면 플래그
            if not quotes and len(narration.strip()) > 20:
                flags.append({
                    "check": "CHECK 9",
                    "block_id": b_id,
                    "severity": "warning",
                    "original": narration[:100] + ("..." if len(narration) > 100 else ""),
                    "suggestion": "evidence_quotes empty. Verify narration does not contain unanchored product-specific data.",
                    "auto_fixed": False
                })
    return flags

# ============================================================
# CHECK 10 — Cross-Block Repetition Scan (블록 간 구문 반복 감지)
# 동일한 종결구/도입구가 3회 이상 반복되면 플래그
# Voice audit Issue 3-A 대응: "슬롯머신" 핸드오프 패턴 감지
# ============================================================
def check_10_cross_block_repetition(draft):
    """블록 간 동일 종결구/도입구 반복 감지"""
    flags = []
    
    # -- 모든 블록의 narration에서 첫 문장과 마지막 문장 추출
    openings = []  # (block_id, first_sentence)
    closings = []  # (block_id, last_sentence)
    
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            b_id = block.get('block_id', '')
            narration = block.get('narration', '').strip()
            if not narration:
                continue
            
            # 문장 분리 (마침표, 물음표, 느낌표 기준)
            sentences = re.split(r'(?<=[.!?])\s+', narration)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if sentences:
                openings.append((b_id, sentences[0]))
                closings.append((b_id, sentences[-1]))
    
    # -- 종결구 반복 감지 (정규화 후 비교)
    def normalize(text):
        """구두점/관사 제거 후 소문자 정규화"""
        text = text.lower().strip()
        text = re.sub(r'[.!?,;:\'"\u201c\u201d]', '', text)
        text = re.sub(r'\b(the|a|an|and|this|that)\b', '', text)
        return re.sub(r'\s+', ' ', text).strip()
    
    # 종결구 그룹핑
    closing_groups = {}
    for b_id, sentence in closings:
        key = normalize(sentence)
        if key not in closing_groups:
            closing_groups[key] = []
        closing_groups[key].append((b_id, sentence))
    
    for key, group in closing_groups.items():
        if len(group) >= 3:
            block_ids = [g[0] for g in group]
            phrase = group[0][1]
            flags.append({
                "check": "CHECK 10",
                "block_id": ", ".join(block_ids),
                "severity": "warning",
                "original": f"Closing phrase repeated {len(group)}x: \"{phrase}\"",
                "suggestion": f"Rewrite closing phrase in {len(group) - 1} of these blocks to create unique handoffs.",
                "auto_fixed": False
            })
    
    # 도입구 그룹핑 (동일한 구문 구조)
    opening_groups = {}
    for b_id, sentence in openings:
        key = normalize(sentence)
        if key not in opening_groups:
            opening_groups[key] = []
        opening_groups[key].append((b_id, sentence))
    
    for key, group in opening_groups.items():
        if len(group) >= 3:
            block_ids = [g[0] for g in group]
            phrase = group[0][1]
            flags.append({
                "check": "CHECK 10",
                "block_id": ", ".join(block_ids),
                "severity": "warning",
                "original": f"Opening phrase repeated {len(group)}x: \"{phrase}\"",
                "suggestion": f"Rewrite opening phrase in {len(group) - 1} of these blocks for structural variety.",
                "auto_fixed": False
            })
    
    # -- "[Product Name], however" 패턴 반복 감지 (Issue 3-D)
    however_blocks = []
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            b_id = block.get('block_id', '')
            narration = block.get('narration', '')
            if re.search(r'The \w[\w\s]+, however,', narration):
                however_blocks.append(b_id)
    
    if len(however_blocks) >= 2:
        flags.append({
            "check": "CHECK 10",
            "block_id": ", ".join(however_blocks),
            "severity": "warning",
            "original": f"\"[Product], however,\" pattern repeated {len(however_blocks)}x",
            "suggestion": "Vary laggard openings. Use data-led or consequence-led openings instead of name+however.",
            "auto_fixed": False
        })
    
    return flags

# ============================================================
# CHECK 4 보조: Humor 유틸
# tone_data에서 유머 후보 추출 + draft에서 기존 유머 집계
# ============================================================
def extract_humor_candidates(tone_data):
    """tone_data의 contradiction_pairs에서 is_humorous 인용구의 product_id 추출"""
    candidates = []
    for t in tone_data.get('common_themes', []):
        for cp in t.get('contradiction_pairs', []):
            if cp.get('positive_quote', {}).get('is_humorous'):
                candidates.append(cp['positive_quote'].get('product_id'))
            if cp.get('negative_quote', {}).get('is_humorous'):
                candidates.append(cp['negative_quote'].get('product_id'))
    return list(set([c for c in candidates if c]))

def count_existing_humor(draft):
    """draft_script.json에서 is_humorous: true인 인용구 수 집계"""
    count = 0
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            for quote in block.get('evidence_quotes', []):
                if quote.get('is_humorous'):
                    count += 1
    return count

# ============================================================
# CHECK 8 보조: Drama Pattern Detection
# prohibitions.md §2 Narrative Stance 위반 패턴 감지
# 감정 투영, 가상 시나리오, 의인화, 극적 프레이밍을 탐지
# Creative Director가 리라이트 판단 시 참고
# ============================================================

# §2 위반 패턴 — pipeline_contracts.json에서 로드
DRAMA_PATTERNS = contracts()["audit"]["drama_patterns"]

def check_8_drama_patterns(draft):
    """narration에서 §2 Narrative Stance 위반 패턴 감지 (Creative Director 참고용)"""
    flags = []
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            text = block.get('narration', '')
            text_lower = text.lower()
            b_id = block.get('block_id')

            for category, patterns in DRAMA_PATTERNS.items():
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        flags.append({
                            "check": "CHECK 8",
                            "block_id": b_id,
                            "severity": "warning",
                            "original": text[:200] + ("..." if len(text) > 200 else ""),
                            "suggestion": f"Drama pattern detected ({category}): '{match.group()}'. Rewrite in 1st Person Observer voice.",
                            "auto_fixed": False
                        })
    return flags

# ============================================================
# CHECK 11 — Numeric Exile (소수점 백분율 금지)
# narrative_standards.md §1 Numeric Exile Rule 자동 감지
# narration에서 소수점 백분율 (e.g. 63.6%, 7.2%) 패턴 감지
# ============================================================
def check_11_numeric_exile(draft):
    """narration에서 Numeric Exile 위반 감지 (소수점 백분율)"""
    flags = []
    # Matches patterns like: 63.6%, 7.2%, 41.5% (decimal point followed by digit(s) and %)
    decimal_pct_re = re.compile(r'\d+\.\d+\s*%')
    
    for scene in draft.get('scenes', []):
        for block in scene.get('blocks', []):
            text = block.get('narration', '')
            b_id = block.get('block_id')
            
            matches = decimal_pct_re.findall(text)
            for m in matches:
                flags.append({
                    "check": "CHECK 11",
                    "block_id": b_id,
                    "severity": "error",
                    "original": text[:200] + ("..." if len(text) > 200 else ""),
                    "suggestion": f"Numeric Exile violation: '{m}' — convert to human-scale phrasing (e.g. 'six out of ten', 'nearly half').",
                    "auto_fixed": False
                })
    return flags

# ============================================================
# main — CLI 진입점
# 읽기 전용 감사: draft를 수정하지 않고 리포트만 생성
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Script Auditor — mechanical CHECK pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (same behavior, explicit flag for logging)")
    args = parser.parse_args()

    draft_path = "data/draft_script.json"
    # category_validator.json: /check 단계에서 생성된 축소본 재사용
    # (category_tone_editor.json은 존재하지 않는 고스트 프로파일 출력물이었음)
    tone_data_path = "data/category_validator.json"
    outline_path = "data/comparison_outline.json"
    report_path = "tmp/auditor_report.json"

    # 필수 입력 파일 존재 확인
    missing = [p for p in [draft_path, tone_data_path, outline_path] if not os.path.exists(p)]
    if missing:
        print(f"Required input files not found: {', '.join(missing)}")
        sys.exit(1)

    draft = load_json(draft_path)
    tone_data = load_json(tone_data_path)
    outline = load_json(outline_path)

    banned_phrases = parse_prohibitions()

    print(f"\n--- Script Auditor ---")
    print(f"  Parsed {len(banned_phrases)} banned phrases from prohibitions.md")
    if args.dry_run:
        print("  Mode: DRY-RUN (read-only audit)")

    # === CHECK 실행 ===
    # CHECK 0 (BGM Mood), CHECK 5 (Tone Weight) 제거됨
    # — bgm_mood는 directing_hint로 흡수 (architecture_update_plan_v3 Phase 1-1)
    flags_2 = check_2_tension_climax(outline, tone_data)
    flags_3 = check_3_ai_trace_scan(draft, banned_phrases)
    flags_6 = check_6_scene_balance(outline, tone_data)
    flags_8 = check_8_drama_patterns(draft)
    flags_9 = check_9_data_anchoring(draft, outline)
    flags_10 = check_10_cross_block_repetition(draft)
    flags_11 = check_11_numeric_exile(draft)

    humor_cands = extract_humor_candidates(tone_data)
    humor_count = count_existing_humor(draft)

    # 모든 플래그를 단일 배열로 통합 — Creative Director가 flags만 순회하면 됨
    all_flags = flags_2 + flags_3 + flags_6 + flags_8 + flags_9 + flags_10 + flags_11

    # severity별 집계
    error_count = sum(1 for f in all_flags if f.get('severity') == 'error')
    warning_count = sum(1 for f in all_flags if f.get('severity') == 'warning')
    info_count = sum(1 for f in all_flags if f.get('severity') == 'info')

    # 리포트 생성
    report = {
        "flags": all_flags,
        "summary": {
            "total": len(all_flags),
            "error": error_count,
            "warning": warning_count,
            "info": info_count
        },
        "humor_count": humor_count,
        "humor_minimum": contracts()["audit"]["humor_minimum"],
        "humor_candidates": humor_cands,
        "checks_executed": ["CHECK 2", "CHECK 3", "CHECK 6", "CHECK 8", "CHECK 9", "CHECK 10", "CHECK 11"],
        "checks_skipped": ["CHECK 0 (removed: bgm_mood deprecated)", "CHECK 5 (removed: bgm_mood dependent)"]
    }

    # script_auditor는 draft를 수정하지 않음 — 읽기 전용 감사
    save_json(report_path, report)

    # 요약 출력
    print(f"\n  Results:")
    print(f"    CHECK 2 (Tension/Climax): {len(flags_2)} flags")
    print(f"    CHECK 3 (AI Trace):       {len(flags_3)} flags")
    print(f"    CHECK 6 (Scene Balance):  {len(flags_6)} flags")
    print(f"    CHECK 8 (Drama Pattern):  {len(flags_8)} flags")
    print(f"    CHECK 9 (Data Anchoring): {len(flags_9)} flags")
    print(f"    CHECK 10 (Repetition):    {len(flags_10)} flags")
    print(f"    CHECK 11 (Numeric Exile): {len(flags_11)} flags")
    print(f"  Total: {len(all_flags)} flags (error: {error_count}, warning: {warning_count}, info: {info_count})")
    print(f"  Humor: {humor_count}/{report['humor_minimum']} ({'OK' if humor_count >= report['humor_minimum'] else 'BELOW MINIMUM'})")
    print(f"  Report saved: {report_path}")

if __name__ == "__main__":
    main()
