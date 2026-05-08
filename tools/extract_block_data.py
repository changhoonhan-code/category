"""
Block-Level Data Extractor
──────────────────────────
Assembles per-block JSON from multiple pipeline sources:
  - script_output.json   → narration, scene_type, evidence_quotes
  - manifest.json        → audio path, duration, word_timestamps
  - category_analysis.json → theme ranking visualization data
  - DB (amazon_reviews)  → full review body for evidence_reviews
  
Output: data/blocks/<block_id>.json  (one file per block)

Usage:
    python tools/extract_block_data.py                   # all blocks
    python tools/extract_block_data.py active_showdown    # single block
"""
import json
import os
import sys
import re
import pymysql
from bs4 import BeautifulSoup

from config import DATAS_DIR, PROJ_ROOT

OUTPUT_DIR = os.path.join(DATAS_DIR, "blocks")

# ── File loaders ──────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_script_output():
    return load_json(os.path.join(DATAS_DIR, "script_output.json"))

def load_manifest():
    return load_json(os.path.join(DATAS_DIR, "narration_audio", "manifest.json"))


# ── DB review fetcher (reuses review_capture_image.py logic) ──────────────────

DB_HOST = "***REDACTED_IP***"
DB_USER = "***REDACTED_USER***"
DB_PASS = "***REDACTED_PASS***"
DB_NAME = "***REDACTED_DB***"
DB_PORT = 3306

_db_conn = None

def get_db_connection():
    """Singleton DB connection to avoid reconnecting per review."""
    global _db_conn
    if _db_conn is None or not _db_conn.open:
        _db_conn = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS,
            database=DB_NAME, port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
    return _db_conn

def get_html_from_db(review_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT meta FROM amazon_reviews WHERE review_id = %s", (review_id,))
            result = cursor.fetchone()
            if result and "meta" in result:
                return result["meta"]
    except Exception as e:
        print(f"  DB error ({review_id}): {e}")
        global _db_conn
        _db_conn = None  # force reconnect on next call
    return None


# ── HTML → review dict parser ────────────────────────────────────────────────

def parse_review_html(review_id, html_snippet, highlight_phrase=None):
    """Parse Amazon review HTML meta into a structured dict."""
    soup = BeautifulSoup(html_snippet, "html.parser")

    # reviewer name
    name_tag = soup.find("span", class_="a-profile-name")
    reviewer_name = name_tag.text.strip() if name_tag else "Amazon Customer"

    # avatar URL
    avatar_url = ""
    avatar_div = soup.find("div", class_="a-profile-avatar")
    if avatar_div:
        img_tag = avatar_div.find("img")
        if img_tag:
            avatar_url = img_tag.get("data-src") or img_tag.get("src") or ""
            if "grey-pixel.gif" in avatar_url and img_tag.get("data-src"):
                avatar_url = img_tag.get("data-src")

    # star rating
    star_rating = 5
    rating_tag = soup.find("i", {"data-hook": "review-star-rating"})
    if rating_tag:
        alt_span = rating_tag.find("span")
        if alt_span and "out of 5" in alt_span.text:
            try:
                star_rating = int(float(alt_span.text.split()[0]))
            except:
                pass
        else:
            for c in rating_tag.get("class", []):
                if c.startswith("a-star-"):
                    try:
                        star_rating = int(c.replace("a-star-", ""))
                    except:
                        pass

    # title
    title_tag = soup.find("a", {"data-hook": "review-title"})
    if title_tag:
        spans = title_tag.find_all("span")
        title_text = spans[-1].text.strip() if spans else title_tag.text.strip()
        title_text = title_text.replace("5.0 out of 5 stars", "").strip()
    else:
        title_text = ""

    # date
    date_tag = soup.find("span", {"data-hook": "review-date"})
    date_text = date_tag.text.strip() if date_tag else ""

    # verified purchase
    vp_tag = soup.find("span", {"data-hook": "avp-badge"})
    is_verified = bool(vp_tag)

    # variant text
    variant_text = ""
    format_strip = soup.find("div", class_="review-format-strip")
    if format_strip:
        formats = format_strip.find_all("a", class_="a-size-mini")
        for f in formats:
            if "avp-badge" not in f.get("data-hook", "") and f.text:
                variant_text = f.text.strip()
                break

    # body
    body_tag = soup.find("span", {"data-hook": "review-body"})
    review_body = body_tag.text.strip() if body_tag else ""

    # helpful text
    helpful_tag = soup.find("span", {"data-hook": "helpful-vote-statement"})
    if not helpful_tag:
        helpful_tag = soup.find("span", class_="cr-vote-text")
    helpful_text = helpful_tag.text.strip() if helpful_tag else ""

    # review images
    images = []
    img_section = soup.find("div", {"data-hook": "review-image-section"})
    if img_section:
        for img_tag in img_section.find_all("img"):
            src = img_tag.get("data-src") or img_tag.get("src") or ""
            if src and "grey-pixel" not in src:
                images.append(src)

    review_dict = {
        "review_id": review_id,
        "reviewer_name": reviewer_name,
        "avatar_url": f"reviews/avatars/{review_id}.png",
        "rating": star_rating,
        "title": title_text,
        "date_text": date_text,
        "variant_text": variant_text,
        "is_verified": is_verified,
        "body": review_body,
        "helpful_text": helpful_text,
        "images": images,
    }

    if highlight_phrase:
        review_dict["highlight_phrase"] = highlight_phrase

    return review_dict


# ── Word timestamp formatter ─────────────────────────────────────────────────

def format_word_timestamps(raw_timestamps, narration_text):
    """Convert manifest word_timestamps (word/start/end) to enriched format
    with text_start / text_end character offsets."""
    result = []
    search_from = 0

    for entry in raw_timestamps:
        word = entry["word"]
        # Find the word position in narration text
        idx = narration_text.find(word, search_from)
        if idx == -1:
            # Try case-insensitive or partial match
            lower_text = narration_text.lower()
            lower_word = word.lower().rstrip(".,!?;:")
            idx = lower_text.find(lower_word, search_from)

        if idx != -1:
            text_start = idx
            text_end = idx + len(word)
            search_from = text_end
        else:
            # Fallback: use search_from as best guess
            text_start = search_from
            text_end = search_from + len(word)
            search_from = text_end

        result.append({
            "word": word,
            "time_start": round(entry["start"], 2),
            "time_end": round(entry["end"], 2),
            "text_start": text_start,
            "text_end": text_end,
        })

    return result




# ── Main block assembler ─────────────────────────────────────────────────────

def extract_block(scene, block, manifest):
    """Assemble a single block's complete data structure."""
    block_id = block["block_id"]
    narration = block.get("narration", "")
    headline = scene.get("headline", "")

    # ── narration audio ──
    narration_audio = None
    if block_id in manifest:
        m = manifest[block_id]
        narration_audio = {
            "path": f"narration_audio/{block_id}.wav",
            "actual_duration_sec": m.get("actual_duration_sec", 0),
        }

    # ── word timestamps ──
    word_timestamps = []
    if block_id in manifest and "word_timestamps" in manifest[block_id]:
        raw_ts = manifest[block_id]["word_timestamps"]
        word_timestamps = format_word_timestamps(raw_ts, narration)


    # ── evidence reviews (from DB) ──
    evidence_reviews = []
    evidence_quotes = block.get("evidence_quotes", [])
    if evidence_quotes:
        seen_ids = set()
        for eq in evidence_quotes:
            rid = eq.get("review_id")
            if not rid or rid in seen_ids:
                continue
            seen_ids.add(rid)

            highlight = eq.get("highlight_phrase", "")
            html = get_html_from_db(rid)
            if html:
                review_dict = parse_review_html(rid, html, highlight)
                evidence_reviews.append(review_dict)
            else:
                print(f"  [WARN] No DB data for review {rid} in block {block_id}")

    # ── Assemble final structure ──
    result = {
        "scene_type": scene.get("scene_type", ""),
        "block_id": block_id,
        "title": block.get("title", ""),
        "narration": narration,
    }

    if narration_audio:
        result["narration_audio"] = narration_audio

    if headline:
        result["headline"] = headline

    if word_timestamps:
        result["word_timestamps"] = word_timestamps

    if evidence_reviews:
        result["evidence_reviews"] = evidence_reviews

    return result


# ── Entry point ──────────────────────────────────────────────────────────────

def main(target_block_ids=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[*] Loading data sources...")
    script = load_script_output()
    manifest = load_manifest()

    total = 0
    success = 0

    for scene in script.get("scenes", []):
        for block in scene.get("blocks", []):
            block_id = block["block_id"]

            if target_block_ids and block_id not in target_block_ids:
                continue

            total += 1
            print(f"\n[>] Extracting: {block_id}")

            try:
                data = extract_block(scene, block, manifest)
                scene_type = scene.get("scene_type", "unknown")
                out_path = os.path.join(OUTPUT_DIR, f"{scene_type}_{block_id}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"  [OK] Written: {out_path}")
                success += 1
            except Exception as e:
                print(f"  [ERR] Error: {e}")
                import traceback
                traceback.print_exc()

    # Close DB connection
    global _db_conn
    if _db_conn and _db_conn.open:
        _db_conn.close()

    print(f"\n[DONE] {success}/{total} blocks extracted to {OUTPUT_DIR}")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(targets)
