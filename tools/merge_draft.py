import json
import os
import re
import sys

# Ensure tools directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import contracts

# -- Windows cp949 encoding fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_raw_draft_md(md_path):
    """Parse raw_draft.md into structured data matching raw_draft.json format.

    Expected format:
        ## Thought Process
        ...text...

        ## Video Question
        ...text...

        ---

        ### block_id
        ...narration text...

        ### another_block_id
        ...narration text...

    Returns:
        dict with keys: thought_process, video_question, blocks[]
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # -- VETO check: first non-empty line starts with STRUCTURAL_REJECTION:
    first_line = ""
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break

    if first_line.startswith("STRUCTURAL_REJECTION:"):
        reason = first_line.replace("STRUCTURAL_REJECTION:", "").strip()
        return {
            "structural_rejection": {
                "reason": reason,
                "veto_scope": "theme_selection"
            }
        }

    result = {
        "thought_process": "",
        "video_question": "",
        "blocks": []
    }

    # Extract ## Thought Process section
    tp_match = re.search(
        r"^## Thought Process\s*\n(.*?)(?=^## |\Z)",
        content, re.MULTILINE | re.DOTALL
    )
    if tp_match:
        result["thought_process"] = tp_match.group(1).strip()

    # Extract ## Video Question section
    vq_match = re.search(
        r"^## Video Question\s*\n(.*?)(?=^## |^---|\Z)",
        content, re.MULTILINE | re.DOTALL
    )
    if vq_match:
        result["video_question"] = vq_match.group(1).strip()

    # Extract ### block_id sections
    block_pattern = re.compile(
        r"^### (\S+)\s*\n(.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL
    )
    for match in block_pattern.finditer(content):
        block_id = match.group(1)
        narration = match.group(2).strip()
        # Strip markdown formatting from narration (bold, italic, etc.)
        narration = re.sub(r"\*\*(.+?)\*\*", r"\1", narration)  # bold
        narration = re.sub(r"\*(.+?)\*", r"\1", narration)       # italic
        narration = re.sub(r"_(.+?)_", r"\1", narration)         # underscore italic

        result["blocks"].append({
            "block_id": block_id,
            "narration": narration
        })

    return result


def merge_draft():
    # Load pipeline contracts
    ct = contracts()
    script_schema = ct.get("script_schema", {})
    required_root_keys = script_schema.get("required_root_keys", [])
    required_block_keys = script_schema.get("required_block_keys", [])

    # Load input files
    with open('data/comparison_outline.json', encoding='utf-8') as f:
        outline = json.load(f)
    with open('data/category_writer.json', encoding='utf-8') as f:
        writer_data = json.load(f)

    # -- Determine input format: prefer raw_draft.md, fallback to raw_draft.json
    md_path = "data/raw_draft.md"
    json_path = "data/raw_draft.json"

    if os.path.exists(md_path):
        print(f"merge_draft.py: Parsing raw_draft.md (Markdown mode)")
        raw = parse_raw_draft_md(md_path)
    elif os.path.exists(json_path):
        print(f"merge_draft.py: Falling back to raw_draft.json (Legacy JSON mode)")
        with open(json_path, encoding='utf-8') as f:
            raw = json.load(f)
    else:
        print("merge_draft.py: ERROR — neither raw_draft.md nor raw_draft.json found")
        sys.exit(1)

    # -- VETO check
    if "structural_rejection" in raw:
        rejection = raw["structural_rejection"]
        rejection_path = "data/draft_rejection.json"
        with open(rejection_path, 'w', encoding='utf-8') as f:
            json.dump(rejection, f, indent=2, ensure_ascii=False)
        print(f"merge_draft.py: STRUCTURAL REJECTION detected — saved to {rejection_path}")
        print(f"  Reason: {rejection.get('reason', 'unknown')}")
        print(f"  Scope: {rejection.get('veto_scope', 'unknown')}")
        sys.exit(1)

    # Build the block lookup from raw_draft
    blocks_lookup = {b['block_id']: b for b in raw.get('blocks', [])}

    # Initialize final draft structure (dynamically from contracts)
    draft = {}
    for key in required_root_keys:
        if key == "thought_process": draft[key] = raw.get("thought_process", "")
        elif key == "category_name": draft[key] = writer_data.get("category_name", "")
        elif key == "video_question": draft[key] = raw.get("video_question", outline.get("video_question", ""))
        elif key == "products": draft[key] = [{"product_id": p["product_id"], "product_name": p["product_name"]} for p in writer_data.get("products", [])]
        elif key == "excluded_themes": draft[key] = outline.get("excluded_themes", [])
        elif key == "teaser_payoff_map": draft[key] = outline.get("teaser_payoff_map", {})
        elif key == "scenes": draft[key] = []
        else: draft[key] = outline.get(key)
        
    # Inject thought_process even if not in required_root_keys
    if "thought_process" not in draft:
        draft["thought_process"] = raw.get("thought_process", "")

    # Reconstruct scenes with original metadata + new narration
    for scene in outline.get("scenes", []):
        new_scene = {
            "scene_id": scene["scene_id"],
            "scene_type": scene["scene_type"],
            "assigned_themes": scene.get("assigned_themes", []),
            "notes": scene.get("notes", ""),
            "blocks": []
        }
        
        # Add headline mapping for downstream validation
        if scene["scene_type"] != "hook":
            if scene.get("assigned_themes"):
                new_scene["headline"] = scene["assigned_themes"][0]
            elif scene["scene_type"] == "intro_credibility":
                new_scene["headline"] = "Introduction"
            elif scene["scene_type"] == "landmine":
                new_scene["headline"] = "The Landmine"
            elif scene["scene_type"] == "final_recommendation":
                new_scene["headline"] = "Final Recommendation"
            else:
                new_scene["headline"] = scene["scene_id"]
            
        for block_id in scene.get("block_ids", []):
            raw_block = blocks_lookup.get(block_id, {})
            merged_block = {}
            for key in required_block_keys:
                if key == "block_id": merged_block[key] = block_id
                elif key == "narration": merged_block[key] = raw_block.get("narration", f"[[MISSING NARRATION FOR {block_id}]]")
                elif key == "pacing_profile": merged_block[key] = scene.get("block_pacing", {}).get(block_id, "standard")
                elif key == "evidence_quotes": merged_block[key] = []
                else: merged_block[key] = ""
            
            # Additional structural fields
            merged_block["title"] = ""
            new_scene["blocks"].append(merged_block)
            
        draft["scenes"].append(new_scene)

    # Save final assembled script
    with open('data/draft_script.json', 'w', encoding='utf-8') as f:
        json.dump(draft, f, indent=2, ensure_ascii=False)

    # Report missing blocks
    outline_block_ids = set()
    for scene in outline.get("scenes", []):
        for bid in scene.get("block_ids", []):
            outline_block_ids.add(bid)

    missing = outline_block_ids - set(blocks_lookup.keys())
    if missing:
        print(f"merge_draft.py: WARNING — {len(missing)} missing blocks: {', '.join(sorted(missing))}")
    
    input_mode = "MD" if os.path.exists(md_path) else "JSON"
    print(f"merge_draft.py: Successfully merged raw_draft ({input_mode}) into draft_script.json")

if __name__ == '__main__':
    merge_draft()
