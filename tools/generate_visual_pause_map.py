"""
generate_visual_pause_map.py

Phase 2 Step 0.4 — Visual Read Pause Map Generator.

Reads data/script_output.json and produces tmp/visual_pause_map.json
with per-block pause duration based on highlight_phrase word count.

Pause rules (from Narration Agent SKILL.md §6):
  - highlight_phrase ≤ 5 words  → 1.5s
  - highlight_phrase 6–8 words  → 2.0s
  - highlight_phrase 9–10 words → 2.5s

Blocks without evidence_quotes are mapped to null.
"""

import argparse
import json
import sys
from pathlib import Path


def compute_pause_sec(word_count: int) -> float:
    """Return pause duration based on highlight_phrase word count."""
    if word_count <= 5:
        return 1.5
    elif word_count <= 8:
        return 2.0
    else:
        return 2.5


def build_pause_map(script: dict) -> dict:
    """Walk all scenes/blocks and build the pause map."""
    pause_map: dict = {}

    scenes = script.get("scenes", [])
    for scene in scenes:
        blocks = scene.get("blocks", [])
        for block in blocks:
            block_id = block.get("block_id")
            if not block_id:
                continue

            evidence_quotes = block.get("evidence_quotes")
            if not evidence_quotes:
                pause_map[block_id] = None
                continue

            # Use the first evidence_quote's highlight_phrase for pause calc.
            # If multiple quotes exist, use the longest highlight_phrase
            # (viewer needs time to read the most complex one).
            max_word_count = 0
            for eq in evidence_quotes:
                phrase = eq.get("highlight_phrase", "")
                if phrase:
                    wc = len(phrase.split())
                    max_word_count = max(max_word_count, wc)

            if max_word_count == 0:
                pause_map[block_id] = None
                continue

            pause_sec = compute_pause_sec(max_word_count)
            pause_map[block_id] = {
                "pause_sec": pause_sec,
                "word_count": max_word_count,
            }

    return pause_map


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Visual Read Pause map for Narration Agent."
    )
    parser.add_argument(
        "--script",
        default="data/script_output.json",
        help="Path to script_output.json (default: data/script_output.json)",
    )
    parser.add_argument(
        "--output",
        default="tmp/visual_pause_map.json",
        help="Output path (default: tmp/visual_pause_map.json)",
    )
    args = parser.parse_args()

    script_path = Path(args.script)
    output_path = Path(args.output)

    if not script_path.exists():
        print(f"ERROR: {script_path} not found. Run Phase 1 first.", file=sys.stderr)
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    pause_map = build_pause_map(script)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pause_map, f, indent=2, ensure_ascii=False)

    # Summary
    total = len(pause_map)
    with_pause = sum(1 for v in pause_map.values() if v is not None)
    print(f"Visual pause map generated: {output_path}")
    print(f"  Total blocks: {total}")
    print(f"  Blocks with pause: {with_pause}")
    print(f"  Blocks without pause: {total - with_pause}")


if __name__ == "__main__":
    main()