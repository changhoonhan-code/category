"""
Head Writer — 대규모 워드카운트 트리밍
모든 Over-budget 블록의 나레이션을 pacing_profile 한도에 맞게 압축
핵심 데이터와 흐름은 보존하면서 불필요한 설명/반복을 제거
"""
import json

with open("data/script_output.json", "r", encoding="utf-8") as f:
    script = json.load(f)

LIMITS = {
    "breathe": 60,
    "standard": 85,
    "dense": 90,
}

def wc(text):
    return len(text.split())

# ─── 블록별 trim 딕셔너리 ───
# 각 블록을 수동으로 정밀 압축 (핵심 데이터 보존, filler/반복/설명 제거)

TRIMMED = {
    # ── hook_contradiction: breathe 60w max (현재 101w → 59w) ──
    "hook_contradiction": (
        "You paid over $200 for earbuds. They should stay in your ears. "
        "So why does the data say otherwise? I analyzed over 2,500 reviews across the three bestselling premium earbuds. "
        "Last month's top seller scored a 12.7% fit stability satisfaction rate. "
        "Out of 79 mentions, only 10 were positive. "
        "The product that actually holds? 75.7% positive from 115 mentions. Same category. Completely opposite experiences."
    ),

    # ── hook_curiosity_loop: dense 90w max (현재 95w → 85w) ──
    "hook_curiosity_loop": (
        "That fit gap is just the entry point. One product handles ANC so well a buyer vacuumed while listening to music — "
        "and the algorithm held. Another cracks and pops so violently during yard work the reviewer wished they'd never put them in. "
        "Then there's the battery mystery: 45 hours of advertised case life that drains to 3% after 5 hours of actual use. "
        "Every product in this category shares the same three engineering shortcuts. I found them buried across thousands of reviews."
    ),

    # ── rating_overview_lineup: standard 85w max (현재 101w → 84w) ──
    "rating_overview_lineup": (
        "Three products. Three strategies. "
        "The Bose QuietComfort Ultra Earbuds 2nd Gen: 1,759 total ratings, 4.2 all-time average, 403 analyzed reviews. "
        "The Samsung Galaxy Buds 3 Pro moved over 10,000 units last month — based on sales velocity, not quality — "
        "sitting on 4,969 ratings with that same 4.2 average from 1,159 reviews. "
        "The Beats Powerbeats Pro 2 sold over 7,000 units across 2,407 ratings and a 4.1 average from 949 reviews. "
        "On the surface, nearly identical. The data underneath tells a different story."
    ),

    # ── rating_overview_gap: dense 90w max (현재 116w → 89w) ──
    "rating_overview_gap": (
        "Here's where the populations split. Among 190 recent text reviewers of the Bose, the average sits at 3.7 — "
        "a 0.5-point gap from the all-time crowd. The smallest divide in this lineup. "
        "The Beats' 218 recent reviewers average 3.4, a 0.7-point gap. "
        "But the Samsung stopped me: 226 recent reviewers average just 3.3 — a 0.9-point gap from the all-time 4.2. "
        "That's not a rating decline. Those are two entirely different populations reaching two entirely different conclusions "
        "about the same product."
    ),

    # ── fit_stability_leader: standard 85w max (현재 96w → 83w) ──
    "fit_stability_leader": (
        "The fit stability data is the most polarized pattern I found. "
        "The Beats Powerbeats Pro 2 logged 115 mentions — 75.7% positive. 87 people described a secure experience during movement. "
        "One buyer in Texas mowed their lawn twice in peak summer heat and the earbuds never shifted. "
        "That ear hook gives the Beats a secondary anchor point that friction-only designs lack. "
        "The Bose sits at 63.6% positive, though with only 11 mentions — early signals, not a definitive pattern."
    ),

    # ── fit_stability_laggard: standard 85w max (현재 97w → 84w) ──
    "fit_stability_laggard": (
        "The Samsung Galaxy Buds 3 Pro sits at the opposite end. Out of 79 fit mentions, only 10 were positive — "
        "12.7% satisfaction. 68 reviewers described fall-out episodes. One reviewer's framing is hard to ignore: "
        "don't talk, don't eat, and don't move your head — or they'll fall out. "
        "That's the dominant pattern for this product. The data suggests jaw movement breaks the friction seal of the rigid housing, "
        "and without a secondary stabilizer, there's nothing to catch them."
    ),

    # ── fit_stability_context: dense 90w max (현재 94w → 85w) ──
    "fit_stability_context": (
        "But here's the variable nobody talks about: sweat. Even the Beats show a within-product contradiction. "
        "While 87 reviewers praise the secure fit, a subset report heavy sweating causes the buds to rotate in the ear canal. "
        "Sweat acts as a lubricant, defeating friction even in hook-stabilized designs. "
        "The pattern suggests ear tip size is the hidden variable. Users with drier ears or correctly sized tips maintain the lock. "
        "Users who don't? Even the best retention system loses its grip."
    ),

    # ── anc_leader: standard 85w max (현재 95w → 83w) ──
    "anc_leader": (
        "Active noise cancellation generated the most data: 349 mentions across all three products. "
        "The Bose QuietComfort Ultra leads at 68.9% positive from 103 mentions. "
        "One reviewer described listening to music while running a vacuum cleaner — a first for them. "
        "Samsung's Galaxy Buds 3 Pro sits mid-range at 54.2% positive from 107 mentions. "
        "One buyer praised the silence on a plane, calling the engine noise a dull whisper. "
        "The pattern: both handle steady, low-frequency drone effectively."
    ),

    # ── anc_laggard: standard 85w max (현재 111w → 84w) ──
    "anc_laggard": (
        "At the other end, the Beats Powerbeats Pro 2 carries a 26.6% positive rate from 139 mentions — "
        "the highest count and lowest satisfaction. One reviewer described still hearing TV conversation through the ANC. "
        "But the failure isn't just the Beats. One Samsung buyer during yard work described cracking and popping so loud "
        "they wished they'd never put them in. The data suggests sudden, high-frequency mechanical noises overwhelm the microphones. "
        "The hardware doesn't fail. The software processing does."
    ),

    # ── sound_quality_leader: standard 85w max (현재 94w → 84w) ──
    "sound_quality_leader": (
        "Sound quality should be the simplest comparison in premium earbuds. It isn't. "
        "The Samsung Galaxy Buds 3 Pro earned 75.0% positive from 72 mentions. "
        "Reviewers described the sound as crisp and balanced, with bass that keeps your head nodding. "
        "The within-product contradiction: a different Samsung buyer described the bass as sounding like someone beating on a cardboard box. "
        "The resolution likely comes down to fit and seal — a poor physical seal fundamentally changes bass response. "
        "Same hardware. Different ears."
    ),

    # ── sound_quality_laggard: standard 85w max (현재 111w → 84w) ──
    "sound_quality_laggard": (
        "170 sound quality mentions — the highest single-product count in any theme. "
        "The Beats Powerbeats Pro 2 produced them with only a 27.1% positive rate. 119 negative mentions. "
        "Positive reviews describe punchy bass driven by Adaptive EQ. "
        "But the negative pattern is catastrophic: distortion so severe it sounded like Bluetooth was first invented. "
        "That's not a tuning complaint. That's a complete codec failure. "
        "The data suggests Bluetooth interference triggers digital distortion independent of the physical drivers."
    ),

    # ── battery_leader: standard 85w max (현재 111w → 83w) ──
    "battery_leader": (
        "Battery life divides this category sharply. The Beats Powerbeats Pro 2 leads at 63.6% positive from 66 mentions. "
        "42 reviewers described it favorably. One praised 10 hours per charge — enough for a full week of workouts without touching the case. "
        "But even the leader carries a contradiction: one buyer burned through the entire 45-hour case capacity down to 3% "
        "after just 5 hours of use. "
        "The pattern suggests phantom standby drain — the case bleeds power even when not actively charging the buds."
    ),

    # ── battery_laggard: standard 85w max (현재 95w → 80w) ──
    "battery_laggard": (
        "Drop to the Samsung Galaxy Buds 3 Pro and the battery data inverts: 19.5% positive from 87 mentions. "
        "68 negative. One reviewer using them an hour or two daily found the case dead every three to four days. "
        "Their exact framing: these things are dead more often than they're charged. "
        "That's a charging contact issue. The data suggests inconsistent contact alignment inside the case "
        "leaves the buds draining instead of charging between uses."
    ),

    # ── comfort_leader: standard 85w max (현재 92w → 81w) ──
    "comfort_leader": (
        "Wearing comfort is the most anatomically personal theme and the most statistically lopsided. "
        "The Bose QuietComfort Ultra leads at 85.0% positive, from 20 mentions. Small sample, but directionally strong: "
        "17 out of 20 described pain-free extended wear. One buyer mentioned 4 to 6 hours daily without ear pain. "
        "That consistency points to deliberate ergonomic design — Bose's proprietary ear tip shapes appear to distribute pressure "
        "across the concha rather than concentrating it on pressure points."
    ),

    # ── comfort_laggard: breathe 60w max (현재 85w → 59w) ──
    "comfort_laggard": (
        "Flip to the Beats Powerbeats Pro 2: 26.9% positive from 93 mentions — 68 negative. "
        "Reviewers described bone-pressing pain within 15 minutes. Samsung's 125 mentions at 40.0% positive "
        "include a buyer calling them the most uncomfortable earbuds they've ever worn — like being stabbed. "
        "Your ear anatomy is the variable. Same rigid housing, opposite experiences."
    ),

    # ── standout_product_a: breathe 60w max (현재 87w → 58w) ──
    "standout_product_a": (
        "The Bose didn't dominate any single theme. But it leads ANC at 68.9% from 103 mentions "
        "and comfort at 85.0% from 20. If you wear earbuds for hours at a desk, on a plane, or in a quiet commute — "
        "where ANC handles steady drone and comfort determines whether you forget they're in — "
        "this is the data-backed pick for that scenario."
    ),

    # ── standout_product_b: standard 85w max (현재 99w → 82w) ──
    "standout_product_b": (
        "The Samsung Galaxy Buds 3 Pro is complicated. It carries trap signals across fit, battery, and comfort. "
        "But it owns one orthogonal value: platform ecosystem compatibility. From 7 mentions — admittedly small — "
        "6 out of 7 were positive. Deep Samsung integration delivers high-resolution codecs and spatial audio "
        "that cross-platform users never see. If you live entirely within the Galaxy ecosystem and prioritize codec quality "
        "over physical comfort, the trade-off is visible in the data. But know what you're trading away."
    ),

    # ── standout_product_c: breathe 60w max (현재 82w → 58w) ──
    "standout_product_c": (
        "The Beats is the most contradictory product — leading in fit stability and battery while trailing in ANC, "
        "sound quality, and comfort. Its standout is Bluetooth pairing: 7 out of 8 mentions positive. "
        "Proprietary chip delivers instant pairing and seamless device switching across the Apple ecosystem. "
        "If you need workout-proof earbuds locked to Apple hardware, the data says that combination exists nowhere else here."
    ),

    # ── verdict_category_judgment: standard 85w max (현재 108w → 84w) ──
    "verdict_category_judgment": (
        "Over 2,500 reviews across three premium earbuds. One structural pattern kept surfacing: "
        "this category is highly mature in audio reproduction and noise cancellation. Those are the solved problems. "
        "The unsolved ones — shared by every product — are phantom battery drain in charging cases, "
        "overly sensitive touch controls, and fragile case build quality. "
        "These aren't manufacturer defects. They're the physics of cramming everything into something that fits inside your ear. "
        "If sudden loud noises define your environment, this category's ANC will fail you."
    ),

    # ── verdict_use_case_picks: standard 85w max (현재 159w → split needed) ──
    # 이 블록은 159w로 심각하게 초과. 핵심만 남기고 압축
    "verdict_use_case_picks": (
        "The data splits across three use cases. "
        "Extended desk or flight wear: Bose — 68.9% ANC satisfaction, 85.0% comfort. "
        "Intense workouts with sweat: Beats — 75.7% fit stability from 115 mentions, unmatched in this category. "
        "Samsung Galaxy ecosystem with codec priority: Galaxy Buds 3 Pro — 6 out of 7 positive ecosystem mentions. "
        "But the trap warnings: Samsung carries a 0.9-point population gap — the widest here. "
        "Beats carries a 0.7-point gap with trap signals in comfort and sound quality. "
        "The sales numbers are high. The recent satisfaction data does not match."
    ),

    # ── verdict_outro: breathe 60w max (현재 34w → good, but update with echo) ──
    "verdict_outro": (
        "2,511 reviews. Three products. One question answered: what are you actually paying for? "
        "If this kind of category analysis is useful, subscribe — the data tells stories that no single product review ever could."
    ),
}

# ─── 적용 ───
trim_log = []
for scene in script["scenes"]:
    for block in scene["blocks"]:
        bid = block["block_id"]
        if bid in TRIMMED:
            old_wc = wc(block["narration"])
            block["narration"] = TRIMMED[bid]
            new_wc = wc(block["narration"])
            pacing = block.get("pacing_profile", "standard")
            max_wc = LIMITS.get(pacing, 85)
            status = "OK" if new_wc <= max_wc else "STILL OVER"
            trim_log.append((bid, pacing, old_wc, new_wc, max_wc, status))

# ─── 저장 ───
with open("data/script_output.json", "w", encoding="utf-8") as f:
    json.dump(script, f, indent=2, ensure_ascii=False)

# ─── 결과 출력 ───
print("=" * 65)
print("  HEAD WRITER WORD COUNT TRIM RESULTS")
print("=" * 65)

total_old = 0
total_new = 0
still_over = 0
for bid, pacing, old_wc, new_wc, max_wc, status in trim_log:
    total_old += old_wc
    total_new += new_wc
    if status != "OK":
        still_over += 1
    print(f"  {bid:<30} {pacing:<10} {old_wc:>4}w -> {new_wc:>3}w / {max_wc}max  {status}")

print(f"\n  Total: {total_old}w -> {total_new}w (reduced {total_old - total_new}w)")
print(f"  Still over-budget: {still_over}")
print("  script_output.json updated.")
