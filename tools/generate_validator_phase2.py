import json

draft_path = "d:/GEMINI/tmp/script_validator.json"
output_path = "d:/GEMINI/tmp/script_validator_edited.json"
precheck_report_path = "d:/GEMINI/tmp/precheck_report.json"

with open(draft_path, "r", encoding="utf-8") as f:
    script = json.load(f)

with open(precheck_report_path, "r", encoding="utf-8") as f:
    precheck = json.load(f)

additions = []

# CHECK 1: "fourteen thousand reviews" in intro_lineup
additions.append({
    "editor": "Data Validator",
    "block_id": "intro_lineup",
    "fix_type": "[Data Warning]",
    "original": "We pulled over fourteen thousand reviews on these three",
    "corrected": "N/A",
    "reason": "Narration claims 'fourteen thousand reviews' but source is 4,318 analyzed reviews (or 10,608 total ratings)."
})

# CHECK 10: Flags from precheck
for flag in precheck.get("flags_for_llm", []):
    if flag["check"] == "CHECK 10":
        additions.append({
            "editor": "Data Validator",
            "block_id": flag["block_id"],
            "fix_type": "[Placement Warning]",
            "original": flag["detail"],
            "corrected": "N/A",
            "reason": f"Product focus rule relaxed because narration explicitly compares multiple products' failure modes in this block."
        })
    elif flag["check"] == "CHECK 4":
        additions.append({
            "editor": "Data Validator",
            "block_id": "global",
            "fix_type": "[Coverage Warning]",
            "original": flag["detail"],
            "corrected": "N/A",
            "reason": "Themes are covered under 'metric_chapter' scene_type instead of 'theme_*' scene names."
        })

# CHECK 11: "63% satisfaction"
# Just flag it per CHECK 11 (numeric exile, though not decimal, it's still a percentage that might need human scale if strict)
# Rule says "Decimal percentages are PROHIBITED". "63%" is not a decimal. We don't flag.
# Wait, "positive rates of 21%, 18%, and 8%" - same, no decimals.

# CHECK 7: Population Warning?
# intro_gap: "The AirPods Pro 3 sits at a 4.4 all-time..." - It doesn't use "reviews" or "ratings" here, just "all-time". "hundred five-star ratings" is correct.
# landmine_product_c: "experiencing a meaningful drop between their all-time scores and their recent scores. The AirPods gap is 0.4 points." - This is fine.

out_json = {
    "critique_log_additions": additions,
    "block_patches": []
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=2)

print("Generated script_validator_edited.json")
