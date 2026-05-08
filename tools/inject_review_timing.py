"""
Review Timing — Step 3: Inject Timing into Block JSONs
──────────────────────────────────────────────────────
Reads the orchestrator's timing output (tmp/review_timing_output.json)
and injects display_start_sec / display_end_sec into each block's
evidence_reviews in data/blocks/*.json.

Input:  tmp/review_timing_output.json
Output: Updates data/blocks/{scene_type}_{block_id}.json in-place

Usage:
    python tools/inject_review_timing.py
"""
import json
import os
import sys

from config import DATAS_DIR, TMP_DIR

BLOCKS_DIR = os.path.join(DATAS_DIR, "blocks")
TIMING_PATH = os.path.join(TMP_DIR, "review_timing_output.json")


def validate_timing(block_entry, audio_duration):
    """Validate timing assignments for a single block."""
    errors = []
    review_id = block_entry.get("block_id", "?")
    assignments = block_entry.get("assignments", [])
    
    if not assignments:
        errors.append(f"[{review_id}] No assignments found")
        return errors
    
    prev_end = -1.0
    for i, a in enumerate(assignments):
        rid = a.get("review_id", "?")
        start = a.get("display_start_sec", -1)
        end = a.get("display_end_sec", -1)
        
        # Check bounds
        if start < 0:
            errors.append(f"[{review_id}/{rid}] display_start_sec={start} is negative")
        if end > audio_duration + 0.5:
            errors.append(f"[{review_id}/{rid}] display_end_sec={end} exceeds audio duration {audio_duration}")
        if end <= start:
            errors.append(f"[{review_id}/{rid}] display_end_sec={end} <= display_start_sec={start}")
        
        # Check ordering (should be chronological)
        if start < prev_end - 0.1:  # small tolerance
            errors.append(f"[{review_id}/{rid}] Overlaps with previous review (start={start} < prev_end={prev_end})")
        
        prev_end = end
    
    return errors


def main():
    # Load timing output
    if not os.path.exists(TIMING_PATH):
        print(f"[ERR] Timing output not found: {TIMING_PATH}")
        print("      Run the /timing workflow Step 2 (orchestrator mapping) first.")
        sys.exit(1)
    
    with open(TIMING_PATH, "r", encoding="utf-8") as f:
        timing_data = json.load(f)
    
    blocks_timing = timing_data.get("blocks", [])
    print(f"[*] Loaded timing for {len(blocks_timing)} blocks")
    
    # Build lookup: block_id → assignments
    timing_map = {}
    for bt in blocks_timing:
        timing_map[bt["block_id"]] = bt
    
    # Process each block file
    total = 0
    updated = 0
    errors_total = 0
    
    for bf in sorted(os.listdir(BLOCKS_DIR)):
        if not bf.endswith(".json"):
            continue
        
        path = os.path.join(BLOCKS_DIR, bf)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        block_id = data.get("block_id", "")
        if block_id not in timing_map:
            continue
        
        total += 1
        bt = timing_map[block_id]
        audio_duration = data.get("narration_audio", {}).get("actual_duration_sec", 0)
        
        # Validate
        errs = validate_timing(bt, audio_duration)
        if errs:
            print(f"\n[WARN] Validation issues for {block_id}:")
            for e in errs:
                print(f"  - {e}")
            errors_total += len(errs)
        
        # Build review_id → timing lookup
        assign_map = {}
        for a in bt.get("assignments", []):
            assign_map[a["review_id"]] = a
        
        # Inject timing into evidence_reviews
        evidence = data.get("evidence_reviews", [])
        for rev in evidence:
            rid = rev["review_id"]
            if rid in assign_map:
                a = assign_map[rid]
                rev["display_start_sec"] = round(a["display_start_sec"], 2)
                rev["display_end_sec"] = round(a["display_end_sec"], 2)
                if "matched_sentence" in a:
                    rev["matched_sentence"] = a["matched_sentence"]
        
        # Write back
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        updated += 1
        print(f"  [OK] {block_id}: {len(assign_map)} reviews timed")
    
    print(f"\n[DONE] {updated}/{total} blocks updated")
    if errors_total:
        print(f"[WARN] {errors_total} validation warnings — review above")
    else:
        print("[OK] All timing validated successfully")


if __name__ == "__main__":
    main()
