"""
Head Writer Briefing 생성기 — auditor_report.json의 CHECK 10 플래그와
draft_script.json의 block_annotations를 통합하여
Head Writer가 읽을 수 있는 텍스트 브리핑으로 변환.

Head Writer는 JSON 블록 구조가 아닌 연속 텍스트로 작업하므로,
block_id 대신 head_writer_input.txt의 paragraph 번호(빈 줄 기준)로
위치를 알려준다.

핵심 전략:
  - auditor_report.json에서 반복된 원문 문구를 추출
  - draft_script.json에서 block_annotations를 추출
  - head_writer_input.txt에서 block별 narration을 검색하여 paragraph 번호 산출
  - block_id 매핑에 의존하지 않으므로 draft↔output 블록 구성 차이에 면역

입력:
  - tmp/auditor_report.json (script_auditor.py 출력)
  - tmp/head_writer_input.txt (extract_monologue.py 출력)
  - data/draft_script.json (block_annotations 소스 — CD가 생성)

출력:
  - tmp/head_writer_briefing.txt (Head Writer 통합 브리핑)

Usage:
    python tools/generate_briefing.py
"""
import json
import os
import re
import sys

from config import DATAS_DIR, TMP_DIR


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_phrase_in_paragraphs(paragraphs, original_text):
    """head_writer_input.txt의 paragraph 리스트에서 반복 문구가 포함된 paragraph 번호들 반환.

    Args:
        paragraphs: 빈 줄로 분리된 paragraph 텍스트 리스트
        original_text: CHECK 10 flag의 original 필드 전체

    Returns:
        list of 1-indexed paragraph numbers
    """
    # -- CHECK 10의 original 필드에서 실제 반복 문구 추출
    # -- 형식: 'Closing phrase repeated 3x: "The reviews tell the same story."'
    # -- 또는: '"[Product], however," pattern repeated 2x'
    quoted = re.findall(r'"([^"]+)"', original_text)

    if not quoted:
        return []

    # -- 첫 번째 따옴표 내용이 실제 반복 문구
    search_text = quoted[0].lower()

    locations = []
    for i, para in enumerate(paragraphs):
        if search_text in para.lower():
            locations.append(i + 1)  # 1-indexed

    return locations


def find_block_paragraph(paragraphs, draft, block_id):
    """block_id에 해당하는 narration이 위치한 paragraph 번호를 반환한다.

    draft_script.json에서 해당 block_id의 narration 첫 문장을 추출하고,
    head_writer_input.txt의 paragraph에서 검색하여 위치를 찾는다.

    Args:
        paragraphs: 빈 줄로 분리된 paragraph 텍스트 리스트
        draft: draft_script.json 전체 데이터
        block_id: 찾을 block_id

    Returns:
        1-indexed paragraph number, or None if not found
    """
    # draft에서 block_id의 narration 추출
    narration = None
    for scene in draft.get("scenes", []):
        for block in scene.get("blocks", []):
            if block.get("block_id") == block_id:
                narration = block.get("narration", "")
                break
        if narration is not None:
            break

    if not narration:
        return None

    # narration의 첫 40자(정규화)로 paragraph 검색
    search_key = narration[:40].strip().lower()
    if not search_key:
        return None

    for i, para in enumerate(paragraphs):
        if search_key in para.lower():
            return i + 1  # 1-indexed

    return None


# ── 브리핑 섹션 생성기 ────────────────────────────────────────────────────

def generate_check10_section(check_10_flags, paragraphs):
    """CHECK 10 반복 플래그 섹션을 생성한다."""
    if not check_10_flags:
        return []

    lines = []
    lines.append("=" * 60)
    lines.append("REPETITION AUDIT — Automated flags from script_auditor.py")
    lines.append("=" * 60)
    lines.append("")

    for i, flag in enumerate(check_10_flags, 1):
        original = flag.get("original", "")

        # -- head_writer_input.txt에서 직접 문구 검색
        if paragraphs:
            locations = find_phrase_in_paragraphs(paragraphs, original)
            if locations:
                para_str = ", ".join(str(p) for p in locations)
                location_line = f"  Location:   Paragraphs {para_str} (of {len(paragraphs)} total)"
            else:
                location_line = "  Location:   (phrase not found in current monologue — may have been edited upstream)"
        else:
            location_line = "  Location:   (monologue not yet generated — run extract_monologue.py first)"

        lines.append(f"--- Flag {i} ---")
        lines.append(f"  Issue:      {original}")
        lines.append(location_line)
        lines.append(f"  Action:     {flag.get('suggestion', '')}")
        lines.append("")

    return lines


def generate_collision_section(annotations, paragraphs, draft):
    """COLLISION MAP 섹션을 생성한다."""
    collision_anns = [a for a in annotations if a.get("collision_sentence") is not None]
    if not collision_anns:
        return []

    lines = []
    lines.append("=" * 60)
    lines.append("COLLISION MAP — Data points and intended handoffs (Flexible placement)")
    lines.append("=" * 60)
    lines.append("")

    for i, ann in enumerate(collision_anns, 1):
        bid = ann["block_id"]
        para_num = find_block_paragraph(paragraphs, draft, bid)
        sentence_num = ann["collision_sentence"]

        if para_num:
            location = f"Paragraph {para_num}, sentence {sentence_num}"
        else:
            location = f"(block '{bid}' not mapped to paragraph — sentence {sentence_num})"

        lines.append(f"--- Collision {i} ---")
        lines.append(f"  Location:   {location}")
        lines.append(f"  Intent:     Data collision — strongest stat placement")

        handoff = ann.get("residue_handoff")
        if handoff:
            lines.append(f"  Handoff:    {handoff} (Transform this mechanical link into a conversational bridge)")

        lines.append(f"  Action:     Data content must be preserved, but position is completely flexible for organic flow.")
        lines.append("")

    return lines


def generate_humor_section(annotations, paragraphs, draft):
    """HUMOR MARKERS 섹션을 생성한다."""
    humor_anns = [a for a in annotations if a.get("humor_position") is not None]
    if not humor_anns:
        return []

    lines = []
    lines.append("=" * 60)
    lines.append("HUMOR MARKERS — Preserve comedic timing")
    lines.append("=" * 60)
    lines.append("")

    for i, ann in enumerate(humor_anns, 1):
        bid = ann["block_id"]
        para_num = find_block_paragraph(paragraphs, draft, bid)
        humor_pos = ann["humor_position"]

        if para_num:
            location = f"Paragraph {para_num}, quote {humor_pos}"
        else:
            location = f"(block '{bid}' not mapped — quote {humor_pos})"

        lines.append(f"--- Humor {i} ---")
        lines.append(f"  Location:   {location}")
        lines.append(f"  Action:     Maintain ironic tone in surrounding narration.")
        lines.append("")

    return lines


def generate_flow_section(annotations, paragraphs, draft):
    """FLOW NOTES 섹션을 생성한다."""
    flow_anns = [a for a in annotations if a.get("flow_note")]
    if not flow_anns:
        return []

    lines = []
    lines.append("=" * 60)
    lines.append("FLOW NOTES — Intentional narrative devices")
    lines.append("=" * 60)
    lines.append("")

    for i, ann in enumerate(flow_anns, 1):
        bid = ann["block_id"]
        para_num = find_block_paragraph(paragraphs, draft, bid)
        note = ann["flow_note"]

        if para_num:
            location = f"Paragraph {para_num}"
        else:
            location = f"(block '{bid}' not mapped)"

        lines.append(f"--- Flow {i} ---")
        lines.append(f"  Location:   {location}")
        lines.append(f"  Note:       {note}")
        lines.append(f"  Action:     Preserve or sharpen this transition.")
        lines.append("")

    return lines


def main():
    report_path = os.path.join(TMP_DIR, "auditor_report.json")
    input_txt_path = os.path.join(TMP_DIR, "head_writer_input.txt")
    draft_path = os.path.join(DATAS_DIR, "draft_script.json")
    output_path = os.path.join(TMP_DIR, "head_writer_briefing.txt")

    # -- 입력 파일 로드
    report = load_json(report_path)
    draft = load_json(draft_path) or {}

    # -- CHECK 10 플래그 추출
    check_10_flags = []
    if report:
        check_10_flags = [f for f in report.get("flags", []) if f.get("check") == "CHECK 10"]

    # -- block_annotations 추출
    annotations = draft.get("block_annotations", [])

    # -- 어떤 소스도 없으면 브리핑 불필요
    if not check_10_flags and not annotations:
        print("[generate_briefing] No CHECK 10 flags or annotations. No briefing needed.")
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(0)

    # -- head_writer_input.txt에서 paragraph 분리 (빈 줄 기준)
    paragraphs = []
    if os.path.exists(input_txt_path):
        with open(input_txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        paragraphs = content.split("\n\n")

    # -- 통합 브리핑 텍스트 생성
    lines = []

    # 헤더
    lines.append("Read the full monologue FIRST to absorb the overall flow.")
    lines.append("Then, during your polish pass, address these specific flags:")
    lines.append("")

    # 섹션별 생성 — 각 섹션은 소스가 없으면 빈 리스트 반환
    section_count = 0

    check10_lines = generate_check10_section(check_10_flags, paragraphs)
    if check10_lines:
        lines.extend(check10_lines)
        section_count += 1

    collision_lines = generate_collision_section(annotations, paragraphs, draft)
    if collision_lines:
        lines.extend(collision_lines)
        section_count += 1

    humor_lines = generate_humor_section(annotations, paragraphs, draft)
    if humor_lines:
        lines.extend(humor_lines)
        section_count += 1

    flow_lines = generate_flow_section(annotations, paragraphs, draft)
    if flow_lines:
        lines.extend(flow_lines)
        section_count += 1

    # 푸터
    lines.append("=" * 60)
    lines.append("IMPORTANT: Do NOT revert to block-level thinking.")
    lines.append("Use paragraph numbers only as location hints.")
    lines.append("Your goal remains a cohesive, continuous monologue.")
    lines.append("=" * 60)

    # -- 파일 저장
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[generate_briefing] {section_count} sections -> {output_path}")
    print(f"  CHECK 10 flags: {len(check_10_flags)}")
    print(f"  Annotations:    {len(annotations)} "
          f"(collision: {len([a for a in annotations if a.get('collision_sentence') is not None])}, "
          f"humor: {len([a for a in annotations if a.get('humor_position') is not None])}, "
          f"flow: {len([a for a in annotations if a.get('flow_note')])})")


if __name__ == "__main__":
    main()

