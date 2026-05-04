"""
Head Writer Phase A-3 -- 수정된 독백 텍스트를 script_output.json에 안전 병합.

수정된 텍스트 파일(tmp/head_writer_output.txt)을 빈 줄 기준으로 분리하고,
블록 매핑 파일(tmp/head_writer_block_map.json)의 순서대로 block_id에 1:1 매핑하여
script_output.json의 narration 필드만 교체한다.

안전장치:
  - 문단 수 != 블록 수 -> FATAL (병합 중단)
  - 숫자 무결성 검증: 원본과 수정본의 숫자 토큰을 비교하여 변경 시 경고
  - 빈 narration 검출 시 경고

Usage:
    python tools/merge_monologue.py
"""
import json
import os
import re
import sys

from config import DATAS_DIR, TMP_DIR

# -- 기본 경로 --
DEFAULT_TEXT = os.path.join(TMP_DIR, "head_writer_output.txt")
DEFAULT_MAP = os.path.join(TMP_DIR, "head_writer_block_map.json")
DEFAULT_SCRIPT = os.path.join(DATAS_DIR, "script_output.json")


def extract_numbers(text: str) -> list[str]:
    """텍스트에서 모든 숫자 토큰을 추출한다. (무결성 비교용)"""
    return re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)


def main():
    # -- 입력 파일 존재 확인 --
    for path, label in [
        (DEFAULT_TEXT, "Rewritten text"),
        (DEFAULT_MAP, "Block map"),
        (DEFAULT_SCRIPT, "Script"),
    ]:
        if not os.path.exists(path):
            print(f"[merge_monologue] ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    # -- 데이터 로드 --
    with open(DEFAULT_TEXT, "r", encoding="utf-8") as f:
        rewritten_text = f.read().strip()

    with open(DEFAULT_MAP, "r", encoding="utf-8") as f:
        block_map = json.load(f)

    with open(DEFAULT_SCRIPT, "r", encoding="utf-8") as f:
        script = json.load(f)

    # -- 텍스트를 빈 줄 기준으로 분리 --
    paragraphs = rewritten_text.split("\n\n")
    block_ids = block_map["block_ids"]
    expected_count = block_map["block_count"]

    # -- 문단 수 검증 (불일치 시 즉시 중단) --
    if len(paragraphs) != expected_count:
        print(f"[merge_monologue] FATAL: Paragraph count mismatch!", file=sys.stderr)
        print(f"  Expected: {expected_count} blocks", file=sys.stderr)
        print(f"  Received: {len(paragraphs)} paragraphs", file=sys.stderr)
        print(f"  Block IDs: {block_ids}", file=sys.stderr)
        sys.exit(1)

    # -- block_id -> 수정된 narration 매핑 구축 --
    rewrite_map = dict(zip(block_ids, paragraphs))

    # -- 병합 실행 + 숫자 무결성 검증 --
    changes = 0
    unchanged = 0
    number_warnings = []
    empty_warnings = []

    for scene in script.get("scenes", []):
        for block in scene.get("blocks", []):
            bid = block["block_id"]
            if bid not in rewrite_map:
                continue

            original = block.get("narration", "").strip()
            rewritten = rewrite_map[bid].strip()

            # 빈 narration 검출
            if not rewritten:
                empty_warnings.append(bid)
                continue

            # 변경 여부 판단
            if original == rewritten:
                unchanged += 1
                continue

            # 숫자 무결성 검증 (원본에 있던 숫자가 수정본에도 존재하는지)
            orig_nums = extract_numbers(original)
            new_nums = extract_numbers(rewritten)
            if orig_nums != new_nums:
                number_warnings.append({
                    "block_id": bid,
                    "original_numbers": orig_nums,
                    "rewritten_numbers": new_nums,
                })

            # narration 교체
            block["narration"] = rewritten
            changes += 1

    # -- 경고 출력 --
    if empty_warnings:
        print(f"\n[merge_monologue] WARNING: Empty narration in blocks: {empty_warnings}", file=sys.stderr)

    if number_warnings:
        print(f"\n[merge_monologue] NUMBER INTEGRITY WARNINGS ({len(number_warnings)}):", file=sys.stderr)
        for w in number_warnings:
            print(f"  [{w['block_id']}]", file=sys.stderr)
            print(f"    Original:  {w['original_numbers']}", file=sys.stderr)
            print(f"    Rewritten: {w['rewritten_numbers']}", file=sys.stderr)
        print(f"  Numbers should NOT change during voice polish.", file=sys.stderr)

    # -- 저장 --
    with open(DEFAULT_SCRIPT, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    # -- 최종 요약 --
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"  Monologue Merge Complete", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"  Changed:          {changes} blocks", file=sys.stderr)
    print(f"  Unchanged:        {unchanged} blocks", file=sys.stderr)
    print(f"  Number warnings:  {len(number_warnings)}", file=sys.stderr)
    print(f"  Empty warnings:   {len(empty_warnings)}", file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)

    # -- 머신 파싱용 JSON 요약 (stdout) --
    print(json.dumps({
        "status": "success",
        "changes": changes,
        "unchanged": unchanged,
        "number_warnings": len(number_warnings),
        "output": DEFAULT_SCRIPT,
    }))


if __name__ == "__main__":
    main()
