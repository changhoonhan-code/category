import json
import os
import sys

# -- Windows cp949 인코딩 에러 방지 (em-dash 등 유니코드 문자 출력)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def build_hook_scene(blueprint):
    hc = blueprint.get('selected_hook_contradiction', {})
    
    source = hc.get('source', 'unknown')
    theme_name = hc.get('theme_name', 'unknown')
    product_ids = ", ".join(hc.get('product_ids', []))
    drama_score = hc.get('drama_score', 'N/A')
    
    # -- hook_tactical_brief.json에서 시간 예산 + 시나리오 씨앗 로드
    tactical_brief_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "hook_tactical_brief.json")
    time_budget_str = ""
    scenario_seeds_str = ""
    if os.path.exists(tactical_brief_path):
        tactical = load_json(tactical_brief_path)
        tb = tactical.get('time_budget', {})
        if tb:
            time_budget_str = (f"TIME BUDGET: Stage1={tb.get('stage1_sec', '?')}s, "
                              f"Stage2={tb.get('stage2_sec', '?')}s, "
                              f"Stage3={tb.get('stage3_sec', '?')}s. "
                              f"Rationale: {tb.get('rationale', 'N/A')}. ")
        seeds = tactical.get('scenario_seeds', [])
        if seeds:
            scenario_seeds_str = f"SCENARIO SEEDS (Orchestrator): {' | '.join(seeds)}. "
    
    notes = (f"contradiction_source: {source} ({theme_name}, drama={drama_score}). "
             f"Products: {product_ids}. "
             f"{time_budget_str}"
             f"{scenario_seeds_str}"
             "Stage 1: Category-level question (zero product names. NO 'Fiction Scenarios' like 'Picture yourself...'). "
             "Stage 2: Contradiction reveal with product names as clauses. "
             "Stage 3: 2-3 theme teasers + category intelligence hint. "
             "FLEXIBILITY: Stage 2 can be placed in either hook_contradiction or hook_curiosity_loop based on data density.")
             
    return {
        "scene_id": "hook",
        "scene_type": "hook",
        "block_ids": ["hook_contradiction", "hook_curiosity_loop"],
        "block_pacing": {
            "hook_contradiction": "breathe",
            "hook_curiosity_loop": "dense"
        },
        "assigned_themes": [theme_name] if theme_name and theme_name != "unknown" else [],
        "notes": notes
    }

def build_overview_scene(blueprint, cat_data):
    products = cat_data.get('products', [])
    product_names = [p.get('product_name', '') for p in products]
    
    largest_gap_prod = max(products, key=lambda x: x.get('population_gap', 0), default={})
    
    traps = [p.get('product_id') for p in products if p.get('trap_candidate', {}).get('is_trap')]
    trap_str = f"trap_signal: {', '.join(traps)} is_trap=true — hint but reserve full exposé for Landmine." if traps else ""
    
    notes = (f"Target Products: {', '.join(product_names)}. "
             f"Insight: {largest_gap_prod.get('product_id', 'unknown')} shows a massive expectation gap ({largest_gap_prod.get('population_gap', 0)}). "
             f"{trap_str} "
             "Narrative Directive: Establish credibility by mentioning the massive review dataset organically. "
             "Do not sound like a news anchor reading a methodology report. Keep it conversational and focus on the hidden truth behind the star ratings.")
             
    return {
        "scene_id": "intro_credibility",
        "scene_type": "intro_credibility",
        "block_ids": ["intro_lineup", "intro_gap"],
        "block_pacing": {
            "intro_lineup": "standard",
            "intro_gap": "dense"
        },
        "assigned_themes": [],
        "notes": notes.strip()
    }

# -- narrative_weight 기반 블록 수 결정 로직
# -- pipeline_contracts.json에서 로드 (참조: pacing_profiles.md §4 + §6)
from config import contracts
_block = contracts()["block_structure"]
NARRATIVE_WEIGHT_MAP = _block["narrative_weight_map"]
TEMPLATE_SUFFIXES = _block["template_suffixes"]

def resolve_block_count(pattern_type, narrative_weight):
    """narrative_weight + pattern_type 조합으로 블록 수를 결정.

    Args:
        pattern_type: category_pattern_type 문자열 (differentiator 등)
        narrative_weight: Blueprint Designer가 출력한 가중치 ("heavy"/"standard"/"light")

    Returns:
        tuple: (block_count, warnings list)
              - block_count: 최종 블록 수
              - warnings: 위반/폴백 발생 시 경고 메시지 리스트
    """
    warnings = []
    weight_map = NARRATIVE_WEIGHT_MAP.get(pattern_type)

    if not weight_map:
        # -- unknown pattern_type → 2블록 폴백
        warnings.append(
            f"UNKNOWN PATTERN TYPE: '{pattern_type}'. "
            f"Fell back to 2 blocks. Verify Blueprint data.")
        return 2, warnings

    count = weight_map.get(narrative_weight)

    if count is None:
        # -- light가 differentiator/mixed에 할당된 경우 (§4 위반)
        warnings.append(
            f"NARRATIVE_WEIGHT VIOLATION: '{narrative_weight}' is not allowed for "
            f"'{pattern_type}' (pacing_profiles.md §4). "
            f"Auto-upgrading to 'standard'.")
        count = weight_map.get('standard', 2)

    if narrative_weight not in ('heavy', 'standard', 'light'):
        # -- 유효하지 않은 weight 값 방어
        warnings.append(
            f"INVALID NARRATIVE_WEIGHT: '{narrative_weight}'. "
            f"Expected 'heavy'/'standard'/'light'. Falling back to 'standard'.")
        count = weight_map.get('standard', 2)

    return count, warnings


def build_theme_scenes(blueprint, cat_data):
    scenes = []
    runtime_warnings = []
    selected_themes = blueprint.get('selected_themes', [])
    common_themes_data = {t.get('theme_name'): t for t in cat_data.get('common_themes', [])}
    
    for theme in selected_themes:
        theme_name = theme.get('theme_name', 'Unknown')
        pattern_type = theme.get('category_pattern_type', 'differentiator')
        directive = theme.get('narrative_directive', '')
        narrative_weight = theme.get('narrative_weight', 'standard')
        
        # -- block_hint 레거시 호환: narrative_weight가 없고 block_hint만 있는 경우
        if 'narrative_weight' not in theme and 'block_hint' in theme:
            bh = theme['block_hint']
            if bh >= 3: narrative_weight = 'heavy'
            elif bh <= 1: narrative_weight = 'light'
            else: narrative_weight = 'standard'
            runtime_warnings.append(
                f"LEGACY COMPAT: theme '{theme_name}' uses deprecated 'block_hint'={bh}. "
                f"Mapped to narrative_weight='{narrative_weight}'. "
                f"Update Blueprint Designer to output 'narrative_weight' directly.")
        
        theme_data = common_themes_data.get(theme_name, {})
        rankings = theme_data.get('rankings', [])
        
        # Metric-centric stats (no leader/laggard identity exposure)
        ratios = [r.get('positive_ratio', 0) for r in rankings]
        spread_pp = round((max(ratios) - min(ratios)) * 100, 1) if ratios else 0
        total_mentions = sum(r.get('mention_count', 0) for r in rankings)
        
        c_pairs = len(theme_data.get('contradiction_pairs', []))
        c_str = f"Leverage contradiction_pairs data ({c_pairs} pairs available)." if c_pairs > 0 else ""
        
        notes = (
            f"narrative_directive: [Blueprint] {directive} | "
            f"[Metric] spread={spread_pp}pp, "
            f"total_mentions={total_mentions}, "
            f"pattern_type={pattern_type}. {c_str}"
        )
        
        safe_prefix = theme_name.split()[0].lower().replace("-", "_")
        
        # -- narrative_weight → 블록 수 결정
        actual_count, weight_warnings = resolve_block_count(pattern_type, narrative_weight)
        runtime_warnings.extend(
            [f"theme '{theme_name}' ({pattern_type}): {w}" for w in weight_warnings])

        block_ids = []
        block_pacing = {}

        if pattern_type == "differentiator":
            # -- Template A: Direct Confrontation (2-3 blocks)
            suffixes = ['_showdown', '_fallout', '_context']
            blocks = [f"{safe_prefix}{s}" for s in suffixes[:actual_count]]
            for b in blocks:
                block_ids.append(b)
                if b.endswith("_context"): block_pacing[b] = "dense"
                else: block_pacing[b] = "standard"

        elif pattern_type == "universal_weakness":
            # -- Template B: Structural Analysis (1-2 blocks)
            suffixes = ['_diagnosis', '_spectrum']
            blocks = [f"{safe_prefix}{s}" for s in suffixes[:actual_count]]
            for b in blocks:
                block_ids.append(b)
                block_pacing[b] = "standard"

        elif pattern_type == "universal_strength":
            # -- Template C: Value Proof (1 block 고정)
            b = f"{safe_prefix}_baseline"
            block_ids.append(b)
            block_pacing[b] = "standard"

        elif pattern_type == "mixed":
            # -- Template D: Use-Case Split (1-2 blocks)
            suffixes = ['_profiles', '_tradeoff']
            blocks = [f"{safe_prefix}{s}" for s in suffixes[:actual_count]]
            for b in blocks:
                block_ids.append(b)
                block_pacing[b] = "standard"
        else:
            # -- 미지의 pattern_type 방어적 폴백 (중립 접미사 사용 — §6 레거시 접미사 금지 준수)
            blocks = [f"{safe_prefix}_block_1", f"{safe_prefix}_block_2"]
            for b in blocks:
                block_ids.append(b)
                block_pacing[b] = "standard"
            runtime_warnings.append(
                f"UNKNOWN PATTERN TYPE: '{pattern_type}' for theme '{theme_name}'. "
                f"Fell back to generic 2-block structure. Verify Blueprint data.")

        scenes.append({
            "scene_id": f"metric_{safe_prefix}",
            "scene_type": "metric_chapter",
            "block_ids": block_ids,
            "block_pacing": block_pacing,
            "assigned_themes": [theme_name],
            "notes": notes.strip()
        })
        
    return scenes, runtime_warnings

def build_landmine_scene(blueprint, cat_data):
    """Build the Landmine scene — consolidated fatal flaw warnings per product.
    
    Sources: contradiction_pairs (negative), trap_candidate data,
    and any universal_weakness themes.
    """
    products = cat_data.get('products', [])
    if not products:
        return None

    block_ids = []
    block_pacing = {}
    notes_parts = []

    # Gather contradiction data per product for fatal flaw identification
    common_themes = {t.get('theme_name'): t for t in cat_data.get('common_themes', [])}
    
    for p in products:
        pid = p.get('product_id')
        b_id = f"landmine_{pid}"
        block_ids.append(b_id)
        block_pacing[b_id] = "standard"
        
        # Check trap candidate status
        trap = p.get('trap_candidate', {})
        trap_str = "TRAP CANDIDATE. " if trap.get('is_trap') else ""
        
        # Find worst-performing themes for this product
        worst_themes = []
        for tname, tdata in common_themes.items():
            for r in tdata.get('rankings', []):
                if r.get('product_id') == pid and r.get('positive_ratio', 1) < 0.3:
                    worst_themes.append(f"{tname}({r['positive_ratio']*100:.0f}%)")
        
        worst_str = f"Weak metrics: {', '.join(worst_themes)}. " if worst_themes else ""
        notes_parts.append(f"{b_id}: {trap_str}{worst_str}Expose this critical flaw organically.")

    return {
        "scene_id": "landmine",
        "scene_type": "landmine",
        "block_ids": block_ids,
        "block_pacing": block_pacing,
        "assigned_themes": [],
        "notes": "THE LANDMINE: This section exposes the fatal flaw of each product. "
                 "Narrative Directive: Deliver a sharp, cynical warning about what the brand isn't telling buyers. "
                 "CRITICAL: Do NOT use the same sentence structure or template for each product. "
                 "Vary your opening phrases and transition naturally. "
                 + " ".join(notes_parts)
    }

def build_final_recommendation_scene(blueprint, cat_data):
    """Build the Final Recommendation scene — absorbs verdict + standout.
    
    Each product gets a verdict block that leads with its unique strength
    (standout data), then the use-case fit, then the trap warning callback.
    """
    v_sources = blueprint.get('final_recommendation_sources', blueprint.get('verdict_sources', {}))
    # -- trap_products: computed from source data, not blueprint pass-through
    trap_prods = [p.get('product_id') for p in cat_data.get('products', [])
                  if p.get('trap_candidate', {}).get('is_trap')]
    buy_if = v_sources.get('buy_if_themes', [])
    skip_if = v_sources.get('skip_if_themes', [])
    
    # -- Absorb standout data into recommendation notes
    unique_strengths_map = {}
    for us in cat_data.get('unique_strengths', []):
        pid = us.get('product_id')
        if pid:
            unique_strengths_map[pid] = us
    
    standout_notes = []
    for pid, us_data in unique_strengths_map.items():
        theme_label = us_data.get('theme_name', '')
        why_label = us_data.get('why_unique', '')
        use_label = us_data.get('recommended_use_case', '')
        standout_notes.append(f"standout_{pid}: {theme_label}. why_unique: {why_label}. use_case: {use_label}.")
    
    standout_str = " STANDOUT DATA (absorbed): " + " ".join(standout_notes) if standout_notes else ""
    
    notes = (
        "recommendation_category_judgment: reference category_intelligence organically. "
        "recommendation_use_case_picks: Frame as conditional tradeoffs, not cliché YouTuber endorsements. "
        "Do NOT use phrases like 'Product X is the clear choice for...' or 'Product Y is the best bet if...'. "
        "Provide a brutally honest summary of who should buy what, acknowledging the compromises. "
        "recommendation_notebook: Integrate analyst_notebook insights naturally. "
        f"trap_warning: {', '.join(trap_prods)}. "
        f"buy_if_sources: [{', '.join(buy_if)}]. "
        f"skip_if_sources: [{', '.join(skip_if)}]."
        f"{standout_str}"
    )
    
    return {
        "scene_id": "final_recommendation",
        "scene_type": "final_recommendation",
        "block_ids": ["recommendation_category_judgment", "recommendation_use_case_picks", "recommendation_notebook", "recommendation_outro"],
        "block_pacing": {
            "recommendation_category_judgment": "standard",
            "recommendation_use_case_picks": "standard",
            "recommendation_notebook": "breathe",
            "recommendation_outro": "breathe"
        },
        "assigned_themes": [],
        "notes": notes
    }

def build_teaser_payoff(blueprint, scenes):
    """Teaser/Payoff 자동 배치 + pacing_profiles.md SS4 거리 3 이내 검증.
    
    Args:
        blueprint: comparison_blueprint.json 데이터 (hook contradiction 테마 참조)
        scenes: 조립된 씬 리스트
    
    Returns:
        tuple: (teaser_payoff_map dict, distance_warnings list)
    """
    # -- 거리 검증 하드룰: pacing_profiles.md SS4 "Teaser -> Payoff: Must resolve within 3 scenes."
    MAX_TEASER_DISTANCE = contracts()["pacing"]["max_teaser_distance"]
    distance_warnings = []
    
    hook_idx = -1
    target_idx = -1
    target_scene_id = ""
    target_theme = ""
    
    # -- Hook contradiction 테마 식별 (blueprint에서 참조)
    hook_contradiction = blueprint.get('selected_hook_contradiction', {})
    hook_theme = hook_contradiction.get('theme_name', '')
    
    for i, s in enumerate(scenes):
        if s['scene_type'] == 'hook':
            hook_idx = i
        elif s['scene_type'] == 'metric_chapter' and target_idx == -1:
            # -- Hook contradiction 테마와 매칭되는 씬 우선 탐색
            scene_themes = s.get('assigned_themes', [])
            if hook_theme and hook_theme in scene_themes:
                target_idx = i
                target_scene_id = s['scene_id']
                target_theme = hook_theme
            elif not hook_theme:
                # -- 테마 매칭 불가 시 첫 번째 metric_chapter 씬으로 폴백
                target_idx = i
                target_scene_id = s['scene_id']
                if scene_themes:
                    target_theme = scene_themes[0]
    
    # -- Hook 테마 매칭 실패 시 첫 번째 metric_chapter으로 최종 폴백
    if hook_idx != -1 and target_idx == -1:
        for i, s in enumerate(scenes):
            if s['scene_type'] == 'metric_chapter':
                target_idx = i
                target_scene_id = s['scene_id']
                if s.get('assigned_themes'):
                    target_theme = s['assigned_themes'][0]
                break
                
    if hook_idx != -1 and target_idx != -1:
        distance = target_idx - hook_idx - 1
        
        # -- 거리 3 이내 검증 (pacing_profiles.md SS4 하드룰)
        if distance > MAX_TEASER_DISTANCE:
            distance_warnings.append(
                f"TEASER DISTANCE VIOLATION: hook -> {target_scene_id} distance={distance} "
                f"(max {MAX_TEASER_DISTANCE}). Consider reordering scenes to bring "
                f"'{target_theme}' theme closer to hook."
            )
        
        scenes[hook_idx]['notes'] += f" teaser_payoff: resolved in {target_scene_id} (distance={distance})."
        scenes[target_idx]['notes'] += f" teaser_payoff: resolved here (from hook)."
        
        return {
            "hook_curiosity_loop": {
                "teaser": f"{target_theme} gap (Short-term Bridge)",
                "resolved_in": target_scene_id,
                "distance_scenes": distance
            }
        }, distance_warnings
        
    return {}, distance_warnings

def enforce_runtime_guard(scenes, product_count):
    caps = contracts()["block_structure"]["runtime_caps"]
    max_blocks = caps.get(str(product_count), 27)
    
    compression_log = []
    
    total_blocks = sum(len(s['block_ids']) for s in scenes)
    
    if total_blocks > max_blocks:
        for s in reversed(scenes):
            if total_blocks <= max_blocks: break
            if s['scene_type'] == 'metric_chapter':
                b_ids = s['block_ids']
                if len(b_ids) > 2:
                    removed = b_ids.pop()
                    del s['block_pacing'][removed]
                    total_blocks -= 1
                    compression_log.append(f"Removed {removed} to meet block cap.")
                    
        if total_blocks > max_blocks:
            for s in scenes:
                if s['scene_type'] == 'landmine' and len(s['block_ids']) > 1:
                    while total_blocks > max_blocks and len(s['block_ids']) > 1:
                        removed = s['block_ids'].pop()
                        del s['block_pacing'][removed]
                        total_blocks -= 1
                        compression_log.append(f"Removed {removed} landmine to meet block cap.")
                        
    return {
        "total_blocks": total_blocks,
        "block_cap": max_blocks,
        "compression_log": compression_log
    }

def verify_pacing_distribution(scenes, runtime_meta):
    """페이싱 분포 검증: 연속 dense 금지(하드룰) + 비율 가이드라인 검증.
    
    pacing_profiles.md SS1 Block Distribution Rules:
    - breathe: 15-25% (가이드라인)
    - standard: 55-70% (가이드라인)
    - dense: 10-15% (가이드라인)
    - 연속 dense 금지 (하드룰 — TTS 품질 제약)
    """
    # -- 비율 가이드라인 범위 — pipeline_contracts.json에서 로드
    _guidelines = contracts()["pacing"]["distribution_guidelines"]
    PACING_GUIDELINES = {
        k: (v["min"], v["max"]) for k, v in _guidelines.items()
    }
    
    # -- 1단계: 연속 dense 감지 + 자동 조정 (하드룰)
    all_pacings = []
    for s in scenes:
        new_blocks = s['block_ids']
        for b_id in new_blocks:
            p = s['block_pacing'][b_id]
            if p == 'dense' and all_pacings and all_pacings[-1]['pacing'] == 'dense':
                s['block_pacing'][b_id] = 'standard'
                p = 'standard'
                runtime_meta['compression_log'].append(f"Changed {b_id} from dense to standard to avoid consecutive dense blocks.")
            all_pacings.append({"id": b_id, "pacing": p})
    
    # -- 2단계: 비율 계산 + 가이드라인 검증 (소프트룰 — 경고만 기록)
    total = len(all_pacings)
    if total == 0:
        return
    
    counts = {'breathe': 0, 'standard': 0, 'dense': 0}
    for entry in all_pacings:
        p = entry['pacing']
        if p in counts:
            counts[p] += 1
    
    # -- 비율 계산 결과를 runtime_metadata에 기록
    ratios = {}
    for profile, count in counts.items():
        ratios[profile] = {
            'count': count,
            'ratio': round(count / total * 100, 1)
        }
    runtime_meta['pacing_distribution'] = ratios
    
    # -- 가이드라인 범위 벗어남 감지 + compression_log 기록
    for profile, (lo, hi) in PACING_GUIDELINES.items():
        actual_ratio = counts[profile] / total
        lo_pct = int(lo * 100)
        hi_pct = int(hi * 100)
        actual_pct = round(actual_ratio * 100, 1)
        
        if actual_ratio < lo:
            runtime_meta['compression_log'].append(
                f"PACING GUIDELINE: {profile} is {actual_pct}% ({counts[profile]}/{total} blocks), "
                f"below target range {lo_pct}-{hi_pct}%. Data may justify this — review manually."
            )
        elif actual_ratio > hi:
            runtime_meta['compression_log'].append(
                f"PACING GUIDELINE: {profile} is {actual_pct}% ({counts[profile]}/{total} blocks), "
                f"above target range {lo_pct}-{hi_pct}%. Data may justify this — review manually."
            )

# ═══════════════════════════════════════════════════════════════════════════════
# Energy Curve Validation — warn on consecutive universal_weakness scenes
# (Ordering is Blueprint Designer's responsibility; this is a guardrail only)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_pattern_type(scene):
    """Extract category_pattern_type from a metric_chapter scene's notes."""
    notes = scene.get('notes', '')
    for pt in ('differentiator', 'universal_weakness', 'universal_strength', 'mixed'):
        if f'pattern_type={pt}' in notes:
            return pt
    return 'unknown'


def validate_scene_order(theme_scenes):
    """Validate that Blueprint Designer's theme order follows energy curve rules.

    Does NOT reorder — only logs warnings for Blueprint Designer to fix upstream.

    Checks:
    1. Consecutive universal_weakness scenes (energy dip)
    2. Last metric chapter is universal_weakness (weak Verdict lead-in)

    Returns:
        list: warning messages (empty if order is clean)
    """
    warnings = []

    if len(theme_scenes) <= 1:
        return warnings

    types = [_get_pattern_type(s) for s in theme_scenes]
    ids = [s.get('scene_id', '') for s in theme_scenes]

    # -- Check 1: consecutive universal_weakness
    for i in range(len(types) - 1):
        if types[i] == 'universal_weakness' and types[i + 1] == 'universal_weakness':
            warnings.append(
                f"ENERGY CURVE WARNING: Consecutive universal_weakness scenes "
                f"'{ids[i]}' → '{ids[i + 1]}' (positions {i},{i + 1}). "
                f"Back-to-back 'nobody wins' chapters create a sustained energy dip. "
                f"Fix in Blueprint Designer: interleave a differentiator between them.")

    # -- Check 2: last metric chapter is universal_weakness
    if types and types[-1] == 'universal_weakness':
        warnings.append(
            f"ENERGY CURVE NOTE: Last metric chapter '{ids[-1]}' is universal_weakness. "
            f"Consider ending with a differentiator for stronger Verdict lead-in.")

    return warnings


def main():
    blueprint_path = "data/comparison_blueprint.json"
    # -- blueprint 프로파일 출력을 직접 참조 (별도 structure_engineer 프로파일 불필요)
    cat_data_path = "data/category_blueprint.json"
    output_path = "data/comparison_outline.json"
    
    if not os.path.exists(blueprint_path) or not os.path.exists(cat_data_path):
        print("Required input files not found. Run filter_category.py first.")
        sys.exit(1)
        
    blueprint = load_json(blueprint_path)
    cat_data = load_json(cat_data_path)
    
    scenes = []
    scenes.append(build_hook_scene(blueprint))
    scenes.append(build_overview_scene(blueprint, cat_data))
    theme_scenes, theme_warnings = build_theme_scenes(blueprint, cat_data)
    
    # -- Energy curve validation: warn on consecutive universal_weakness
    energy_warnings = validate_scene_order(theme_scenes)
    theme_warnings.extend(energy_warnings)
    
    scenes.extend(theme_scenes)
    
    landmine = build_landmine_scene(blueprint, cat_data)
    if landmine: scenes.append(landmine)
        
    scenes.append(build_final_recommendation_scene(blueprint, cat_data))
    
    teaser_map, distance_warnings = build_teaser_payoff(blueprint, scenes)
    runtime = enforce_runtime_guard(scenes, cat_data.get('product_count', 3))
    
    # -- 거리 위반 경고 + 테마 빌드 경고를 compression_log에 병합
    runtime['compression_log'].extend(distance_warnings)
    runtime['compression_log'].extend(theme_warnings)
    
    verify_pacing_distribution(scenes, runtime)
    
    outline = {
        "video_question": blueprint.get("video_question", ""),
        "excluded_themes": blueprint.get("excluded_themes", []),
        "scenes": scenes,
        "teaser_payoff_map": teaser_map,
        "runtime_metadata": runtime
    }
    
    save_json(output_path, outline)
    
    # -- 실행 요약 출력
    print(f"Outline generated with {runtime['total_blocks']} blocks. Cap: {runtime['block_cap']}.")
    
    # -- 페이싱 분포 출력
    if 'pacing_distribution' in runtime:
        dist = runtime['pacing_distribution']
        print(f" Pacing: breathe={dist['breathe']['count']}({dist['breathe']['ratio']}%) "
              f"standard={dist['standard']['count']}({dist['standard']['ratio']}%) "
              f"dense={dist['dense']['count']}({dist['dense']['ratio']}%)")
    
    # -- 압축/경고 로그 출력
    for log in runtime['compression_log']:
        print(f" - {log}")

if __name__ == "__main__":
    main()
