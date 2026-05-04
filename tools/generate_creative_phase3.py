import json

output_path = "d:/GEMINI/tmp/script_creative_edited.json"

critique_log = [
    {
        "editor": "Creative Director",
        "block_id": "landmine_product_a",
        "fix_type": "Flag Resolution",
        "original": "Drama pattern detected (fiction_scenario): 'picture a'.",
        "corrected": None,
        "reason": "CHECK 8 Warning: Rewrite in 1st Person Observer voice without fiction scenarios."
    },
    {
        "editor": "Creative Director",
        "block_id": "hook_curiosity_loop",
        "fix_type": "Flag Resolution",
        "original": "Every single one of these products has a recent rating problem...",
        "corrected": None,
        "reason": "CHECK 9 Warning: Verify narration does not contain unanchored product-specific data. (Data is anchored to analyst notebook, but flagged by auditor)."
    }
]

quote_patches = [
    {
        "block_id": "battery_fallout",
        "review_id": "RCYFY6LO2SJRA",
        "is_humorous": True
    },
    {
        "block_id": "charging_spectrum",
        "review_id": "RZ17P87DU8FM3",
        "is_humorous": True
    },
    {
        "block_id": "ear_spectrum",
        "review_id": "R1TTI0SENLREW6",
        "is_humorous": True
    }
]

block_annotations = [
    {
        "block_id": "active_showdown",
        "collision_sentence": 2,
        "residue_handoff": "Moves to environmental breakdown",
        "humor_position": None,
        "flow_note": "Strong data contrast"
    },
    {
        "block_id": "active_fallout",
        "collision_sentence": 3,
        "residue_handoff": "Pivots to structural issues",
        "humor_position": None,
        "flow_note": "Highlights algorithmic weakness"
    },
    {
        "block_id": "active_context",
        "collision_sentence": 3,
        "residue_handoff": "Ends ANC section",
        "humor_position": None,
        "flow_note": "Physical limitation explained"
    },
    {
        "block_id": "battery_showdown",
        "collision_sentence": 2,
        "residue_handoff": "Transitions to competitor flaws",
        "humor_position": None,
        "flow_note": "Immediate subversion of expectations"
    },
    {
        "block_id": "battery_fallout",
        "collision_sentence": 3,
        "residue_handoff": "Ends battery section",
        "humor_position": 4,
        "flow_note": "Dual failure modes discussed"
    },
    {
        "block_id": "charging_diagnosis",
        "collision_sentence": 5,
        "residue_handoff": "Moves to invisible issues",
        "humor_position": None,
        "flow_note": "Aesthetics vs Functionality"
    },
    {
        "block_id": "charging_spectrum",
        "collision_sentence": 4,
        "residue_handoff": "Ends charging section",
        "humor_position": 3,
        "flow_note": "Detailed specific failures"
    },
    {
        "block_id": "ear_diagnosis",
        "collision_sentence": 2,
        "residue_handoff": "Moves to movement issues",
        "humor_position": None,
        "flow_note": "Medical reaction highlights severity"
    },
    {
        "block_id": "ear_spectrum",
        "collision_sentence": 3,
        "residue_handoff": "Ends comfort section",
        "humor_position": 1,
        "flow_note": "Absurd failure modes"
    }
]

out_json = {
    "critique_log_additions": critique_log,
    "quote_patches": quote_patches,
    "block_annotations": block_annotations
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=2)

print("Generated script_creative_edited.json")
