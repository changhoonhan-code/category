"""
Head Writer — 최종 미세 트리밍
남은 4개 Over-budget 블록 (hook_contradiction, standout_a, standout_c, verdict_use_case_picks)
"""
import json

with open("data/script_output.json", "r", encoding="utf-8") as f:
    script = json.load(f)

def wc(text):
    return len(text.split())

FINAL_TRIMS = {
    # hook_contradiction: breathe 60w max, 현재 64w → 60w
    "hook_contradiction": (
        "You paid over $200 for earbuds. They should stay in your ears. "
        "So why does the data say otherwise? I analyzed over 2,500 reviews across three bestselling premium earbuds. "
        "Last month's top seller scored 12.7% fit stability satisfaction. "
        "Out of 79 mentions, only 10 positive. "
        "The product that actually holds? 75.7% from 115 mentions. Same category. Completely opposite experiences."
    ),

    # standout_product_a: breathe 60w max, 현재 62w → 57w
    "standout_product_a": (
        "The Bose didn't dominate any single theme. But it leads ANC at 68.9% from 103 mentions "
        "and comfort at 85.0% from 20. If you wear earbuds for hours at a desk, on a plane, or in a quiet commute — "
        "where ANC handles steady drone and comfort means forgetting they're in — "
        "this is the data-backed pick."
    ),

    # standout_product_c: breathe 60w max, 현재 64w → 56w
    "standout_product_c": (
        "The Beats is the most contradictory product — leading fit stability and battery, trailing ANC, "
        "sound, and comfort. Its standout: Bluetooth pairing, 7 out of 8 mentions positive. "
        "Proprietary chip delivers instant pairing and seamless switching across Apple's ecosystem. "
        "Need workout-proof earbuds locked to Apple? The data says that combination exists nowhere else here."
    ),

    # verdict_use_case_picks: standard 85w max, 현재 92w → 83w
    "verdict_use_case_picks": (
        "The data splits across three use cases. "
        "Extended desk or flight wear: Bose — 68.9% ANC, 85.0% comfort. "
        "Intense workouts: Beats — 75.7% fit stability from 115 mentions, unmatched here. "
        "Samsung Galaxy ecosystem: Galaxy Buds 3 Pro — 6 out of 7 positive ecosystem mentions. "
        "But the trap warnings: Samsung's 0.9-point population gap is the widest. "
        "Beats carries 0.7 with trap signals in comfort and sound. "
        "Sales numbers are high. Recent satisfaction does not match."
    ),
}

for scene in script["scenes"]:
    for block in scene["blocks"]:
        bid = block["block_id"]
        if bid in FINAL_TRIMS:
            block["narration"] = FINAL_TRIMS[bid]

with open("data/script_output.json", "w", encoding="utf-8") as f:
    json.dump(script, f, indent=2, ensure_ascii=False)

LIMITS = {"breathe": 60, "standard": 85, "dense": 90}
print("Final word count check:")
still_over = 0
total = 0
for scene in script["scenes"]:
    for block in scene["blocks"]:
        bid = block["block_id"]
        pacing = block.get("pacing_profile", "standard")
        w = wc(block["narration"])
        mx = LIMITS.get(pacing, 85)
        total += w
        st = "OK" if w <= mx else "OVER"
        if w > mx:
            still_over += 1
        print(f"  {bid:<30} {pacing:<10} {w:>3}w / {mx}max  {st}")

print(f"\nTotal: {total}w")
print(f"Still over-budget: {still_over}")
