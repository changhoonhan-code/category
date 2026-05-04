"""
Head Writer Phase A-1 -- script_output.json에서 narration만 순수 텍스트로 추출.

모든 블록의 narration을 씬 순서대로 빈 줄(두 줄 개행)로 연결한
순수 텍스트 파일(.txt)을 생성한다.
Head Writer 에이전트는 이 텍스트만 읽고 '한 사람의 독백'으로 다듬은 뒤
같은 형식(빈 줄 구분)으로 반환한다.

출력:
  1. tmp/head_writer_input.txt      -- narration만, 블록 간 빈 줄 구분
  2. tmp/head_writer_block_map.json -- 블록 ID 순서 기록 (머지 시 1:1 매핑용)

Usage:
    python tools/extract_monologue.py
"""
import json
import os
import sys

from config import DATAS_DIR, TMP_DIR

# -- 기본 입력 경로 (prepare_script.py가 생성한 최종 스크립트) --
DEFAULT_INPUT = os.path.join(DATAS_DIR, "script_output.json")


def main():
    input_path = DEFAULT_INPUT

    # -- 입력 파일 존재 확인 --
    if not os.path.exists(input_path):
        print(f"[extract_monologue] ERROR: {input_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # -- 씬 순서대로 블록 ID와 narration을 수집 --
    block_ids = []
    narrations = []

    for scene in data.get("scenes", []):
        for block in scene.get("blocks", []):
            bid = block.get("block_id", "UNKNOWN")
            narration = block.get("narration", "")
            block_ids.append(bid)
            narrations.append(narration)

    if not block_ids:
        print("[extract_monologue] ERROR: No blocks found.", file=sys.stderr)
        sys.exit(1)

    # -- 순수 텍스트 파일 생성 (블록 간 빈 줄 구분) --
    os.makedirs(TMP_DIR, exist_ok=True)
    txt_path = os.path.join(TMP_DIR, "head_writer_input.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(narrations))

    # -- 블록 매핑 파일 생성 (머지 시 순서 복원용) --
    map_path = os.path.join(TMP_DIR, "head_writer_block_map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump({
            "block_ids": block_ids,
            "block_count": len(block_ids),
            "source": input_path,
        }, f, ensure_ascii=False, indent=2)

    # -- 실행 요약 출력 --
    total_words = sum(len(n.split()) for n in narrations)
    print(f"[extract_monologue] {len(block_ids)} blocks -> {txt_path}")
    print(f"[extract_monologue] Block map -> {map_path}")
    print(f"[extract_monologue] --- Block List ---")
    for i, bid in enumerate(block_ids):
        wc = len(narrations[i].split())
        print(f"  [{i + 1:02d}] {bid} ({wc} words)")
    print(f"[extract_monologue] Total: {total_words} words / {len(block_ids)} blocks")


if __name__ == "__main__":
    main()
