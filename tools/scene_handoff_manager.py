"""
Scene Handoff Manager — Sequential N-Block 세션 간 상태 전달 도구.

각 그룹 세션 완료 후, 작성된 tts_prompt_*.txt 파일들을 파싱하여
다음 세션이 필요로 하는 컨텍스트를 tmp/scene_handoff.json에 누적 저장.

Usage:
    python tools/scene_handoff_manager.py --group 1
    python tools/scene_handoff_manager.py --group 2
    python tools/scene_handoff_manager.py --group 3

출력: tmp/scene_handoff.json (누적 모드 — 기존 데이터에 append)
"""
import argparse
import json
import os
import sys
import glob

from config import TMP_DIR, BLOCKS_PER_GROUP
from prompt_utils import extract_prompt_info


HANDOFF_PATH = os.path.join(TMP_DIR, "scene_handoff.json")


def extract_prompt_data(prompt_path: str) -> dict:
    """tts_prompt_{block_id}.txt에서 핵심 정보를 추출.

    prompt_utils.extract_prompt_info()를 래핑하여 기존 인터페이스를 유지.
    """
    return extract_prompt_info(prompt_path)


def find_group_prompts(group_id: str) -> list[str]:
    """현재 그룹에 해당하는 tts_prompt 파일들을 찾아서 스크립트 순서로 반환.

    매칭 전략 (우선순위):
      1. 그룹 스크립트 기반 (script_narration_group{id}.json)
         → 이 파일에 정의된 block_id 목록이 ground truth
         → 해당 tts_prompt 파일이 실제 존재하는지 검증
      2. Fallback: 전체 스크립트 뺄셈 (기존 로직)
         → 그룹 스크립트가 없을 때만 사용
    """
    # 전략 1: 그룹별 필터링 스크립트에서 예상 블록 목록 추출
    group_script_path = os.path.join(TMP_DIR, f"script_narration_group{group_id}.json")
    if os.path.exists(group_script_path):
        with open(group_script_path, "r", encoding="utf-8") as f:
            group_data = json.load(f)

        # 그룹 스크립트에서 블록 ID 목록 추출 (스크립트 순서 보장)
        expected_block_ids = [
            block["block_id"]
            for scene in group_data.get("scenes", [])
            for block in scene.get("blocks", [])
        ]

        # 예상 블록의 tts_prompt 파일 매칭
        group_prompts = []
        missing_blocks = []
        for bid in expected_block_ids:
            prompt_path = os.path.join(TMP_DIR, f"tts_prompt_{bid}.txt")
            if os.path.exists(prompt_path):
                group_prompts.append(prompt_path)
            else:
                missing_blocks.append(bid)

        if missing_blocks:
            print(
                f"[handoff] WARNING: {len(missing_blocks)} expected prompt files not found "
                f"for group {group_id}: {missing_blocks}",
                file=sys.stderr,
            )

        print(
            f"[handoff] Group {group_id}: matched {len(group_prompts)}/{len(expected_block_ids)} "
            f"blocks from {group_script_path}",
            file=sys.stderr,
        )
        return group_prompts

    # 전략 2 (Fallback): 전체 - 이미 처리됨 = 현재 그룹 (레거시 호환)
    print(
        f"[handoff] WARNING: Group script not found at {group_script_path}. "
        f"Falling back to diff-based detection.",
        file=sys.stderr,
    )

    all_prompts = sorted(glob.glob(os.path.join(TMP_DIR, "tts_prompt_*.txt")))
    if not all_prompts:
        return []

    # 이전 그룹에서 이미 처리된 블록 ID 목록
    existing_blocks = set()
    if os.path.exists(HANDOFF_PATH):
        with open(HANDOFF_PATH, "r", encoding="utf-8") as f:
            handoff = json.load(f)
        for entry in handoff.get("delivery_history", []):
            existing_blocks.add(entry["block_id"])

    group_prompts = [
        p for p in all_prompts
        if os.path.basename(p).replace("tts_prompt_", "").replace(".txt", "")
        not in existing_blocks
    ]

    # 전체 스크립트 순서 기반 정렬 시도
    narration_path = os.path.join(TMP_DIR, "script_narration.json")
    if os.path.exists(narration_path):
        with open(narration_path, "r", encoding="utf-8") as f:
            narration_data = json.load(f)
        block_order = {}
        idx = 0
        for scene in narration_data.get("scenes", []):
            for block in scene.get("blocks", []):
                block_order[block["block_id"]] = idx
                idx += 1
        group_prompts.sort(
            key=lambda p: block_order.get(
                os.path.basename(p).replace("tts_prompt_", "").replace(".txt", ""),
                999
            )
        )

    return group_prompts



def update_handoff(group_id: str, prompt_data_list: list[dict]):
    """scene_handoff.json을 누적 업데이트."""
    # 기존 handoff 데이터 로드 (있으면)
    if os.path.exists(HANDOFF_PATH):
        with open(HANDOFF_PATH, "r", encoding="utf-8") as f:
            handoff = json.load(f)
    else:
        handoff = {
            "completed_groups": [],
            "last_block_id": "",
            "last_sentence": "",
            "delivery_history": [],
        }

    # 현재 그룹 데이터 추가 (중복 방지)
    if group_id not in handoff["completed_groups"]:
        handoff["completed_groups"].append(group_id)

    if prompt_data_list:
        # 마지막 블록 정보 업데이트
        last = prompt_data_list[-1]
        handoff["last_block_id"] = last["block_id"]
        handoff["last_sentence"] = last["last_sentence"]

        # 중복된 블록이 있으면 기존 항목 제거 (재실행 시 오염 방지)
        new_block_ids = {pd["block_id"] for pd in prompt_data_list}
        handoff["delivery_history"] = [
            b for b in handoff["delivery_history"] if b["block_id"] not in new_block_ids
        ]

        # delivery_history 누적
        for pd in prompt_data_list:
            handoff["delivery_history"].append({
                "block_id": pd["block_id"],
            })

    # 총 그룹 수 계산 (auto-detect 용)
    # Priority: script_narration.json (full) → group scripts sum → delivery_history (unreliable fallback)
    narration_path = os.path.join(TMP_DIR, "script_narration.json")
    if os.path.exists(narration_path):
        with open(narration_path, "r", encoding="utf-8") as f:
            nd = json.load(f)
        total_blocks = sum(len(s.get("blocks", [])) for s in nd.get("scenes", []))
    else:
        # Try to sum blocks across all existing group scripts
        group_script_blocks = 0
        g = 1
        while True:
            gpath = os.path.join(TMP_DIR, f"script_narration_group{g}.json")
            if not os.path.exists(gpath):
                break
            with open(gpath, "r", encoding="utf-8") as f:
                gd = json.load(f)
            group_script_blocks += sum(len(s.get("blocks", [])) for s in gd.get("scenes", []))
            g += 1
        if group_script_blocks > 0:
            # Group scripts only cover completed groups — use filter_script to get full count
            # Try running filter_script to generate script_narration.json
            import subprocess
            result = subprocess.run(
                ["python", "tools/filter_script.py", "--profile", "narration"],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(HANDOFF_PATH))
            )
            if os.path.exists(narration_path):
                with open(narration_path, "r", encoding="utf-8") as f:
                    nd = json.load(f)
                total_blocks = sum(len(s.get("blocks", [])) for s in nd.get("scenes", []))
            else:
                # Can't determine full count — keep existing total_groups if already set
                total_blocks = handoff.get("total_groups", 1) * BLOCKS_PER_GROUP
                print(
                    "[handoff] WARNING: Cannot determine total block count. "
                    "Run 'python tools/filter_script.py --profile narration' manually.",
                    file=sys.stderr,
                )
        else:
            total_blocks = len(handoff.get("delivery_history", []))
            print(
                "[handoff] WARNING: script_narration.json not found and no group scripts available. "
                "total_groups may be incorrect. Run 'python tools/filter_script.py --profile narration'.",
                file=sys.stderr,
            )
    handoff["total_groups"] = (total_blocks + BLOCKS_PER_GROUP - 1) // BLOCKS_PER_GROUP

    # 저장
    os.makedirs(os.path.dirname(HANDOFF_PATH), exist_ok=True)
    with open(HANDOFF_PATH, "w", encoding="utf-8") as f:
        json.dump(handoff, f, ensure_ascii=False, indent=2)

    return handoff


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Scene Handoff Manager - session state transfer between groups"
    )
    parser.add_argument(
        "--group", type=int,
        help="Completed group number (1-based integer)"
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Rebuild handoff from scratch: re-scan ALL prompt files in script order"
    )
    args = parser.parse_args()

    # --group 또는 --rebuild 중 하나는 필수
    if not args.rebuild and not args.group:
        parser.error("--group 또는 --rebuild 중 하나를 지정해야 합니다.")

    # --rebuild 모드: 모든 프롬프트를 스크립트 순서대로 스캔하여 handoff 재구성
    if args.rebuild:
        print("[handoff] REBUILD mode: re-scanning all prompts from scratch...", file=sys.stderr)
        all_prompts = sorted(glob.glob(os.path.join(TMP_DIR, "tts_prompt_*.txt")))
        if not all_prompts:
            print("[handoff] ERROR: No tts_prompt_*.txt files found.", file=sys.stderr)
            sys.exit(1)

        # 스크립트 순서 기반 정렬
        narration_path = os.path.join(TMP_DIR, "script_narration.json")
        if os.path.exists(narration_path):
            with open(narration_path, "r", encoding="utf-8") as f:
                narration_data = json.load(f)
            block_order = {}
            idx = 0
            for scene in narration_data.get("scenes", []):
                for block in scene.get("blocks", []):
                    block_order[block["block_id"]] = idx
                    idx += 1
            all_prompts.sort(
                key=lambda p: block_order.get(
                    os.path.basename(p).replace("tts_prompt_", "").replace(".txt", ""),
                    999
                )
            )

        # 전체 재구성
        prompt_data_list = []
        for prompt_path in all_prompts:
            data = extract_prompt_data(prompt_path)
            prompt_data_list.append(data)
            print(
                f"  [{data['block_id']}] "
                f"bracket={data['first_bracket'][:40]}...",
                file=sys.stderr,
            )

        # handoff를 처음부터 새로 작성
        total_blocks_count = len(all_prompts)
        max_groups = (total_blocks_count + BLOCKS_PER_GROUP - 1) // BLOCKS_PER_GROUP
        handoff = {
            "completed_groups": [str(i) for i in range(1, max_groups + 1)],
            "total_groups": max_groups,
            "last_block_id": prompt_data_list[-1]["block_id"] if prompt_data_list else "",
            "last_sentence": prompt_data_list[-1]["last_sentence"] if prompt_data_list else "",
            "delivery_history": [
                {
                    "block_id": d["block_id"],
                }
                for d in prompt_data_list
            ],
        }

        os.makedirs(os.path.dirname(HANDOFF_PATH), exist_ok=True)
        with open(HANDOFF_PATH, "w", encoding="utf-8") as f:
            json.dump(handoff, f, ensure_ascii=False, indent=2)

        print(json.dumps({
            "mode": "rebuild",
            "blocks_processed": len(prompt_data_list),
            "handoff_path": HANDOFF_PATH,
        }))
        print(
            f"[handoff] REBUILD complete: {len(prompt_data_list)} blocks processed.",
            file=sys.stderr,
        )
        return

    # 기존 그룹별 모드
    group_id = str(args.group)
    print(f"[handoff] Processing group {group_id}...", file=sys.stderr)

    # 현재 그룹의 프롬프트 파일 찾기
    group_prompts = find_group_prompts(group_id)

    if not group_prompts:
        print(
            f"[handoff] WARNING: No new prompt files found for group {group_id}. "
            "Ensure tts_prompt_*.txt files exist in tmp/.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 각 프롬프트 파일에서 데이터 추출
    prompt_data_list = []
    for prompt_path in group_prompts:
        data = extract_prompt_data(prompt_path)
        prompt_data_list.append(data)
        print(
            f"  [{data['block_id']}] "
            f"bracket={data['first_bracket'][:40]}...",
            file=sys.stderr,
        )

    # Handoff 업데이트
    handoff = update_handoff(group_id, prompt_data_list)

    # 결과 출력
    print(json.dumps({
        "group": group_id,
        "blocks_processed": len(prompt_data_list),
        "total_blocks_cumulative": len(handoff["delivery_history"]),
        "completed_groups": handoff["completed_groups"],
        "handoff_path": HANDOFF_PATH,
    }))

    print(
        f"[handoff] Group {group_id} complete: {len(prompt_data_list)} blocks processed. "
        f"Cumulative: {len(handoff['delivery_history'])} blocks across groups "
        f"{', '.join(handoff['completed_groups'])}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
