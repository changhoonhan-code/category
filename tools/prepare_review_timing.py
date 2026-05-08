"""
Review Timing — Step 1: Prepare Input
──────────────────────────────────────
Reads each block with evidence_quotes from data/blocks/*.json,
splits narration into sentences with time ranges, and packages
minimal review metadata for the orchestrator to perform semantic mapping.

Output: tmp/review_timing_input.json

Usage:
    python tools/prepare_review_timing.py
"""
import json
import os
import re
import sys

from config import DATAS_DIR, TMP_DIR, BLOCKS_PER_GROUP

BLOCKS_DIR = os.path.join(DATAS_DIR, "blocks")
OUTPUT_PATH = os.path.join(TMP_DIR, "review_timing_input.json")


# ── Sentence splitter ────────────────────────────────────────────────────────

def split_into_sentences(text):
    """Split narration text into sentences, handling em-dashes and abbreviations.
    
    Rules:
      - Split on . ? ! followed by whitespace or end-of-string
      - Preserve em-dashes (—) within sentences
      - Handle \\n\\n paragraph breaks as sentence boundaries
      - Don't split on decimal numbers (e.g. "4.4")
    """
    # Replace paragraph breaks with a sentinel
    text = text.replace("\n\n", " ¶ ")
    
    # Split on sentence-ending punctuation followed by space or end
    # Negative lookbehind for digits to avoid splitting "4.4"
    parts = re.split(r'(?<!\d)([.?!])(?:\s+|$)', text)
    
    sentences = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        # Reattach the punctuation if it was captured as a group
        if i + 1 < len(parts) and parts[i + 1] in '.?!':
            chunk += parts[i + 1]
            i += 2
        else:
            i += 1
        
        if not chunk or chunk == '¶':
            continue
        
        # Handle paragraph sentinel — split into separate sentences
        if '¶' in chunk:
            sub_parts = chunk.split('¶')
            for sp in sub_parts:
                sp = sp.strip()
                if sp:
                    sentences.append(sp)
        else:
            sentences.append(chunk)
    
    return sentences


# ── Sentence → Time range mapping ────────────────────────────────────────────

def map_sentences_to_time(sentences, word_timestamps, narration_text):
    """Map each sentence to a (start_sec, end_sec) time range.
    
    Strategy:
      1. Find each sentence's character position in narration_text
      2. Find word_timestamps entries that overlap with that character range
      3. First matching word's time_start → sentence start
      4. Last matching word's time_end → sentence end
    """
    sentence_times = []
    
    search_from = 0
    for sent in sentences:
        # Clean sentence for search (remove trailing punct variations)
        search_text = sent.strip()
        
        # Find sentence position in original narration text
        # Try exact match first
        idx = narration_text.find(search_text, search_from)
        if idx == -1:
            # Try without trailing punctuation
            stripped = search_text.rstrip('.?!')
            idx = narration_text.find(stripped, search_from)
        if idx == -1:
            # Try first 20 chars as anchor
            anchor = search_text[:min(20, len(search_text))]
            idx = narration_text.find(anchor, search_from)
        
        if idx == -1:
            # Fallback: use previous search position
            char_start = search_from
            char_end = search_from + len(search_text)
        else:
            char_start = idx
            char_end = idx + len(search_text)
            search_from = char_end
        
        # Find word timestamps within this character range
        matching_words = []
        for wt in word_timestamps:
            w_start = wt.get("text_start", 0)
            w_end = wt.get("text_end", 0)
            # Word overlaps with sentence if ranges intersect
            if w_end > char_start and w_start < char_end:
                matching_words.append(wt)
        
        if matching_words:
            time_start = matching_words[0]["time_start"]
            time_end = matching_words[-1]["time_end"]
        else:
            # No matching words found — use 0,0 as fallback
            time_start = 0.0
            time_end = 0.0
        
        sentence_times.append({
            "sentence": sent,
            "char_start": char_start,
            "char_end": char_end,
            "time_start": round(time_start, 2),
            "time_end": round(time_end, 2),
            "word_count": len(matching_words),
        })
    
    return sentence_times


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # Collect all block files with evidence_reviews
    block_files = sorted([
        f for f in os.listdir(BLOCKS_DIR)
        if f.endswith(".json")
    ])
    
    blocks_input = []
    
    for bf in block_files:
        path = os.path.join(BLOCKS_DIR, bf)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        evidence = data.get("evidence_reviews", [])
        if not evidence:
            continue
        
        narration = data.get("narration", "")
        word_timestamps = data.get("word_timestamps", [])
        audio_duration = data.get("narration_audio", {}).get("actual_duration_sec", 0)
        
        # Split narration into sentences with time ranges
        sentences = split_into_sentences(narration)
        sentence_times = map_sentences_to_time(sentences, word_timestamps, narration)
        
        # Extract minimal review metadata (no full body — saves context)
        reviews_meta = []
        for rev in evidence:
            reviews_meta.append({
                "review_id": rev["review_id"],
                "highlight_phrase": rev.get("highlight_phrase", ""),
                "rating": rev.get("rating", 0),
                "title": rev.get("title", ""),
            })
        
        blocks_input.append({
            "block_id": data["block_id"],
            "scene_type": data["scene_type"],
            "audio_duration_sec": audio_duration,
            "sentence_count": len(sentence_times),
            "review_count": len(reviews_meta),
            "sentences": sentence_times,
            "reviews": reviews_meta,
        })
    
    # Assign groups (BLOCKS_PER_GROUP blocks per group)
    import math
    total_groups = math.ceil(len(blocks_input) / BLOCKS_PER_GROUP)
    
    output = {
        "total_blocks": len(blocks_input),
        "total_groups": total_groups,
        "blocks_per_group": BLOCKS_PER_GROUP,
        "blocks": blocks_input,
    }
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Prepared {len(blocks_input)} blocks for timing mapping")
    print(f"     Groups: {total_groups} (x{BLOCKS_PER_GROUP} blocks)")
    print(f"     Output: {OUTPUT_PATH}")
    
    # Print summary
    for i, b in enumerate(blocks_input):
        group_num = (i // BLOCKS_PER_GROUP) + 1
        print(f"  [{group_num}] {b['block_id']:35s} "
              f"sentences={b['sentence_count']:2d}  "
              f"reviews={b['review_count']}  "
              f"duration={b['audio_duration_sec']:.1f}s")


if __name__ == "__main__":
    main()
