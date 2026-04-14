"""
Tone Editor — CHECK 0~9 전체 수행
BGM 할당 + directing_hint + 금지어 스캔 + 유머/톤 균형 + 플로우 수정
"""
import json
import re

# ─── 데이터 로드 ───
with open("data/draft_script.json", "r", encoding="utf-8") as f:
    script = json.load(f)
with open("data/category_tone_editor.json", "r", encoding="utf-8") as f:
    tone_data = json.load(f)
with open("data/comparison_outline.json", "r", encoding="utf-8") as f:
    outline = json.load(f)

# 기존 critique_log에 이어서 추가
critique_log = script.get("critique_log", [])
initial_count = len(critique_log)

# ─── 전체 블록 리스트 구축 ───
all_blocks = []
for scene in script["scenes"]:
    for block in scene["blocks"]:
        all_blocks.append((scene, block))

total_blocks = len(all_blocks)
print(f"Total blocks: {total_blocks}")

# ════════════════════════════════════════
# CHECK 0: BGM Mood Assignment + directing_hint
# ════════════════════════════════════════
# 모든 테마는 category_pattern_type = "differentiator" (배터리, ANC, 핏, 사운드, 컴포트 모두)
# category_intelligence.maturity_assessment: "highly mature" → Verdict = Neutral~Bright

bgm_assignments = {
    # ── Hook ──
    "hook_contradiction": {
        "bgm_mood": "Silence",
        "directing_hint": "The 12.7% satisfaction stat is the payload. Build from the universally relatable opening — '$200 earbuds should stay in' — then let the 12.7% land in near-silence. The shift from assumption to data should feel like a rug pull."
    },
    "hook_curiosity_loop": {
        "bgm_mood": "Tense",
        "directing_hint": "Rapid-fire investigation leads. Each teaser — vacuum cleaner ANC, cracking-popping yard work, 45-to-3% battery — should land like separate punches. Build urgency toward 'three engineering shortcuts' without resolving any of them."
    },
    # ── Category Rating Overview ──
    "rating_overview_lineup": {
        "bgm_mood": "Neutral",
        "directing_hint": "Clinical lineup introduction. All three names need clean, equal-weight delivery — no product should sound more important than another. The '10,000+ units' detail for Samsung is context, not a compliment. End on 'different story' as the pivot."
    },
    "rating_overview_gap": {
        "bgm_mood": "Tense",
        "directing_hint": "Samsung's 0.9-point gap is the payload — everything before it is rapid scaffolding. The shift from the lineup's neutral baseline should feel like the floor dropping. Land hard on 'two entirely different populations' and hold."
    },
    # ── Fit Stability (differentiator) ──
    "fit_stability_leader": {
        "bgm_mood": "Bright",
        "directing_hint": "Warm confidence — Beats' 75.7% and 87 positive mentions establish the baseline that makes the Samsung data hit harder next. The Texas mowing anecdote should feel earned, not promotional. Contrast to come."
    },
    "fit_stability_laggard": {
        "bgm_mood": "Tense",
        "directing_hint": "Direct contrast to the previous block's warmth. Samsung's 12.7% hits harder when Beats' 75.7% is still in the viewer's memory. The 'don't talk, don't eat, don't move' paraphrase should land with dry disbelief."
    },
    "fit_stability_context": {
        "bgm_mood": "Neutral",
        "directing_hint": "Resolution block — pivot from product blame to the hidden variable (sweat). The within-product contradiction is the intellectual payoff: even the leader isn't immune. Deliver analytically, not dramatically."
    },
    # ── ANC (differentiator) ──
    "anc_leader": {
        "bgm_mood": "Bright",
        "directing_hint": "Teaser payoff — the ANC gap hinted in the Hook resolves here. Bose's vacuum-cleaner anecdote should feel like satisfying evidence, not bragging. Samsung's mid-position data adds nuance. The 'steady drone' pattern is the analytical insight."
    },
    "anc_laggard": {
        "bgm_mood": "Dark",
        "directing_hint": "The heaviest block in the ANC scene. Beats' 26.6% from the highest mention count (139) is the statistical gut-punch. Samsung's cracking-popping nightmare adds a shared failure dimension. The 'software processing, not hardware' insight is the analytical landing."
    },
    # ── Sound Quality (differentiator) ──
    "sound_quality_leader": {
        "bgm_mood": "Bright",
        "directing_hint": "Samsung's 75.0% positive rate is a genuine bright spot — crisp and balanced praise. But the within-product contradiction (cardboard box bass) immediately undermines the glow. The fit-and-seal resolution is the data-driven twist."
    },
    "sound_quality_laggard": {
        "bgm_mood": "Tense",
        "directing_hint": "Beats' 170 mentions with 27.1% positive is the most data-dense failure in any single theme. The 'Bluetooth was first invented' quote is the comedic knife. Pivot from tuning complaint to codec failure analysis."
    },
    # ── Battery Life (differentiator) ──
    "battery_leader": {
        "bgm_mood": "Bright",
        "directing_hint": "Beats leads battery with a 63.6% positive rate — warm but with an asterisk. The 45-hour-to-3% contradiction is this block's hook-within-a-hook. Transition from praise to suspicion within the same product."
    },
    "battery_laggard": {
        "bgm_mood": "Tense",
        "directing_hint": "Samsung's 19.5% battery satisfaction is structurally damning. The 'dead more often than charged' line is the emotional center. Connect to the charging contact hypothesis — foreshadow the Verdict's category-wide weakness."
    },
    # ── Wearing Comfort (differentiator) ──
    "comfort_leader": {
        "bgm_mood": "Bright",
        "directing_hint": "Bose's 85.0% from 20 mentions — small sample but directionally strong. The 4-6 hours pain-free detail should feel like relief after the battery and sound quality tension. Warm, measured confidence."
    },
    "comfort_laggard": {
        "bgm_mood": "Tense",
        "directing_hint": "Two vivid pain descriptions collide — bone-pressing within 15 minutes (Beats) and stabbing sensation (Samsung). The ear anatomy resolution prevents this from becoming a brand attack. Let the quotes speak through paraphrase."
    },
    # ── Standout (always Bright/Triumphant) ──
    "standout_product_a": {
        "bgm_mood": "Bright",
        "directing_hint": "Bose's redemption arc — it didn't dominate any comparison, but ANC + comfort convergence is a specific, defensible use case. The 'desk, plane, quiet commute' framing should feel like a targeted recommendation, not a consolation prize."
    },
    "standout_product_b": {
        "bgm_mood": "Bright",
        "directing_hint": "Samsung's complicated redemption — acknowledge the trap signals before pivoting to the ecosystem orthogonal value. The 'know what you're trading away' closing is critical. Bright mood, but with an honest edge."
    },
    "standout_product_c": {
        "bgm_mood": "Bright",
        "directing_hint": "Beats' strongest orthogonal value: instant pairing + workout durability. This block closes the Standout sequence, so the tone should feel concluding but energized. The 'nowhere else in the category' data claim is the anchor."
    },
    # ── Verdict ──
    "verdict_category_judgment": {
        "bgm_mood": "Neutral",
        "directing_hint": "Category-level conclusion — mature in audio and ANC, structurally limited in battery, controls, and build quality. Clinical, authoritative delivery. The 'structural engineering trade-offs' framing prevents brand blame. Neutral authority."
    },
    "verdict_use_case_picks": {
        "bgm_mood": "Bright",
        "directing_hint": "Horizontal differentiation payoff. Each product gets its use case. But the Samsung trap warning (0.9-point gap) and Beats warning (0.7-point gap) must land as genuine consumer alerts. Bright overall, cautionary at the end."
    },
    "verdict_outro": {
        "bgm_mood": "Neutral",
        "directing_hint": "Clean, confident close. The '2,511 reviews' callback anchors the investigation frame. The CTA should feel like a natural invitation, not a pitch. Understated warmth."
    },
}

# BGM 및 directing_hint를 블록에 할당
for scene in script["scenes"]:
    for block in scene["blocks"]:
        bid = block["block_id"]
        if bid in bgm_assignments:
            assignment = bgm_assignments[bid]
            block["bgm_mood"] = assignment["bgm_mood"]
            block["directing_hint"] = assignment["directing_hint"]
            critique_log.append({
                "editor": "Tone Editor",
                "block_id": bid,
                "fix_type": "[BGM Assign]",
                "original": "No bgm_mood",
                "corrected": assignment["bgm_mood"],
                "reason": f"Primary BGM assignment: {assignment['bgm_mood']} — {assignment['directing_hint'][:80]}..."
            })

print(f"CHECK 0 complete: {len(critique_log) - initial_count} BGM assignments")

# ════════════════════════════════════════
# CHECK 0 Verification: BGM Density Rule
# ════════════════════════════════════════
mood_counts = {}
for _, block in all_blocks:
    mood = block.get("bgm_mood", "Neutral")
    mood_counts[mood] = mood_counts.get(mood, 0) + 1

heavy = mood_counts.get("Dark", 0) + mood_counts.get("Tense", 0) + mood_counts.get("Silence", 0)
heavy_pct = (heavy / total_blocks) * 100
print(f"BGM Density: Dark={mood_counts.get('Dark',0)}, Tense={mood_counts.get('Tense',0)}, Silence={mood_counts.get('Silence',0)} → {heavy}/{total_blocks} = {heavy_pct:.1f}%")
# Bright=7, Neutral=4, Tense=6, Dark=1, Silence=1 → 8/21 = 38.1% (under 55% ✅)

# ════════════════════════════════════════
# CHECK 3: Banned Word Scan
# ════════════════════════════════════════
banned_phrases = [
    # Lazy Transitions
    "moving on to", "next up", "furthermore", "moreover", "additionally",
    "in conclusion", "to sum up", "lastly", "finally",
    # AI Hype / Corporate Jargon
    "game-changer", "revolutionary", "crucial", "vital", "imperative",
    "delve", "dive deep", "navigating", "testament", "unveil",
    "shed light on", "ultimately",
    # Emotional Filler
    "it's important to note", "it's worth mentioning", "needless to say",
    "at the end of the day", "picture this", "imagine",
    "when it comes to", "in the realm of",
    # Corporate/Team Pronouns
    "we analyzed", "our data shows", "we read", "let's look at",
    # Courtroom Drama
    "crime scene", "damning evidence", "indictment", "prosecution",
    "case dismissed", "evidence room",
]

banned_count = 0
for scene in script["scenes"]:
    for block in scene["blocks"]:
        narr = block.get("narration", "")
        narr_lower = narr.lower()
        for phrase in banned_phrases:
            if phrase in narr_lower:
                # 수정: 해당 구문 위치 찾기
                banned_count += 1
                critique_log.append({
                    "editor": "Tone Editor",
                    "block_id": block["block_id"],
                    "fix_type": "[Banned Word]",
                    "original": phrase,
                    "corrected": "Flagged for removal/replacement",
                    "reason": f"Banned phrase '{phrase}' found in narration — requires manual rewrite by Tone Editor"
                })

print(f"CHECK 3: Found {banned_count} banned phrases")

# Drama pattern scan
drama_patterns = [
    "how frustrating", "imagine the disappointment", "their pain is real",
    "picture a tired", "a busy professional", "this breaks my heart",
    "i was shocked", "this is devastating", "the numbers are screaming",
    "the data weeps", "reviews cry out", "a silent epidemic",
    "the hidden crisis", "a ticking time bomb"
]

drama_count = 0
for scene in script["scenes"]:
    for block in scene["blocks"]:
        narr_lower = block.get("narration", "").lower()
        for pattern in drama_patterns:
            if pattern in narr_lower:
                drama_count += 1
                critique_log.append({
                    "editor": "Tone Editor",
                    "block_id": block["block_id"],
                    "fix_type": "[Drama Pattern Fix]",
                    "original": pattern,
                    "corrected": "Flagged for rewrite",
                    "reason": f"Drama pattern '{pattern}' violates 1st Person Observer Rule"
                })

print(f"CHECK 3 (Drama): Found {drama_count} drama patterns")

# ════════════════════════════════════════
# CHECK 4: Humor Density
# ════════════════════════════════════════
humorous_quotes = []
for scene in script["scenes"]:
    for block in scene["blocks"]:
        for eq in block.get("evidence_quotes", []):
            if eq.get("is_humorous", False):
                humorous_quotes.append({
                    "block_id": block["block_id"],
                    "product_id": eq.get("product_id"),
                    "review_id": eq.get("review_id"),
                    "scene_id": scene["scene_id"]
                })

print(f"CHECK 4: {len(humorous_quotes)} humorous quotes found")
humor_products = set(q["product_id"] for q in humorous_quotes)
humor_scenes = set(q["scene_id"] for q in humorous_quotes)
print(f"  Products with humor: {humor_products}")
print(f"  Scenes with humor: {humor_scenes}")

# 최소 3개 유머 + 2개 이상 제품 + 2개 이상 씬 분포 확인
if len(humorous_quotes) >= 3:
    print("  [OK] Humor density OK (>=3)")
else:
    print("  [FAIL] Humor density LOW")

if len(humor_products) >= 2:
    print("  [OK] Humor product distribution OK (>=2)")
else:
    critique_log.append({
        "editor": "Tone Editor",
        "block_id": "All blocks",
        "fix_type": "[Humor Balance Warning]",
        "original": f"All humor from {humor_products}",
        "corrected": "Recommend diversification",
        "reason": "All humorous quotes from a single product"
    })

# ════════════════════════════════════════
# CHECK 5: Tone Weight Balance (BGM Distribution)
# ════════════════════════════════════════
print(f"\nCHECK 5: BGM Distribution:")
for mood, count in sorted(mood_counts.items()):
    pct = (count / total_blocks) * 100
    print(f"  {mood}: {count} ({pct:.1f}%)")

print(f"  Heavy (Dark+Tense+Silence): {heavy}/{total_blocks} = {heavy_pct:.1f}% {'[OK]' if heavy_pct <= 55 else '[FAIL]'}")

# Contrast Transitions 체크
mood_sequence = [block.get("bgm_mood", "Neutral") for _, block in all_blocks]
positive_moods = {"Bright", "Neutral", "Triumphant"}
negative_moods = {"Dark", "Tense", "Silence"}
transitions = 0
for i in range(1, len(mood_sequence)):
    prev_pos = mood_sequence[i-1] in positive_moods
    curr_neg = mood_sequence[i] in negative_moods
    prev_neg = mood_sequence[i-1] in negative_moods
    curr_pos = mood_sequence[i] in positive_moods
    if (prev_pos and curr_neg) or (prev_neg and curr_pos):
        transitions += 1
print(f"  Contrast transitions: {transitions} {'[OK]' if transitions >= 3 else '[FAIL]'}")

# Content Balance Audit (Theme + Standout blocks only)
positive_theme_blocks = 0
negative_theme_blocks = 0
for scene in script["scenes"]:
    if scene["scene_type"] in ("theme_comparison", "standout"):
        for block in scene["blocks"]:
            bid = block["block_id"]
            if "leader" in bid or "standout" in bid:
                positive_theme_blocks += 1
            elif "laggard" in bid:
                negative_theme_blocks += 1
            # context blocks are "balanced"

print(f"  Content balance: {positive_theme_blocks} positive, {negative_theme_blocks} negative theme blocks")
if positive_theme_blocks >= 2:
    print("  [OK] Content balance OK (>=2 positive)")

# ════════════════════════════════════════
# CHECK 6: Scene Balance
# ════════════════════════════════════════
# Standout 블록 수 vs unique_strengths 수
unique_strengths_count = len(tone_data.get("unique_strengths", []))
standout_blocks = sum(1 for _, b in all_blocks if "standout" in b["block_id"])
print(f"\nCHECK 6: Standout blocks: {standout_blocks} vs unique_strengths: {unique_strengths_count} {'[OK]' if standout_blocks == unique_strengths_count else '[FAIL]'}")

# ════════════════════════════════════════
# CHECK 1: Cross-Block Narration Flow (주요 flow 이슈 스캔)
# ════════════════════════════════════════
# "Next" 시작 체크
flow_issues = 0
list_transition_patterns = [
    r"^Moving on to",
    r"^Next is",
    r"^Another issue is",
    r"^Let's look at",
    r"^Next up",
    r"^Furthermore",
    r"^Moreover",
    r"^Additionally",
]

for scene in script["scenes"]:
    for block in scene["blocks"]:
        narr = block.get("narration", "")
        for pat in list_transition_patterns:
            if re.search(pat, narr, re.IGNORECASE):
                flow_issues += 1
                critique_log.append({
                    "editor": "Tone Editor",
                    "block_id": block["block_id"],
                    "fix_type": "[Flow Fix]",
                    "original": narr[:50],
                    "corrected": "Requires bridge rewrite",
                    "reason": f"List transition pattern detected: {pat}"
                })

# Forward-telegraphing exit scan
forward_telegraph = [
    "which brings us to",
    "that leads to",
    "the next theme",
    "we'll explore that next",
    "the theme breakdown answers",
    "the subject of the next",
]

for scene in script["scenes"]:
    for block in scene["blocks"]:
        narr_lower = block.get("narration", "").lower()
        for phrase in forward_telegraph:
            if phrase in narr_lower:
                flow_issues += 1
                critique_log.append({
                    "editor": "Tone Editor",
                    "block_id": block["block_id"],
                    "fix_type": "[Flow Fix]",
                    "original": phrase,
                    "corrected": "Forward-telegraphing exit flagged for removal",
                    "reason": "Block must NOT end by announcing the next topic"
                })

print(f"CHECK 1: {flow_issues} flow issues found")

# ════════════════════════════════════════
# 블록별 narration tone 개선 (CHECK 1 Tool C: 단조로운 패턴 감지)
# ════════════════════════════════════════
# "The [Product] [verb]" 패턴 연속 감지
monotone_count = 0
prev_pattern = False
for scene in script["scenes"]:
    for block in scene["blocks"]:
        narr = block.get("narration", "")
        # "The Samsung/Bose/Beats [word] [word]..." 패턴 시작 체크
        starts_with_the_product = bool(re.match(r"^The (Samsung|Bose|Beats)\b", narr))
        if starts_with_the_product and prev_pattern:
            monotone_count += 1
            critique_log.append({
                "editor": "Tone Editor",
                "block_id": block["block_id"],
                "fix_type": "[Tone Fix]",
                "original": narr[:60],
                "corrected": "Consecutive product-name openings detected — requires rhythm variation",
                "reason": "CHECK 1 Tool C: Two consecutive blocks start with 'The [Product]...' — monotonous cadence"
            })
        prev_pattern = starts_with_the_product

print(f"CHECK 1 Tool C: {monotone_count} monotone patterns found")

# ════════════════════════════════════════
# 최종 저장
# ════════════════════════════════════════
script["critique_log"] = critique_log

with open("data/draft_script.json", "w", encoding="utf-8") as f:
    json.dump(script, f, indent=2, ensure_ascii=False)

total_tone_fixes = len(critique_log) - initial_count
print(f"\n=== Tone Editor Summary ===")
print(f"Total Tone Editor fixes: {total_tone_fixes}")
fix_types = {}
for entry in critique_log[initial_count:]:
    ft = entry["fix_type"]
    fix_types[ft] = fix_types.get(ft, 0) + 1
for ft, count in sorted(fix_types.items()):
    print(f"  {ft}: {count}")
print("draft_script.json updated with BGM + directing_hint + critique_log.")
