"""
Extract Narration Tool - 최종 스크립트에서 나레이션 텍스트만 가볍게 추출하는 도구
(시맨틱 텍스트 바인딩 연출을 위해 미디어 에이전트에게 제공되는 경량 데이터)

Usage:
    python tools/extract_narration.py --input data/final_script_with_narration.json --output data/narration_only.json
"""
import argparse
import json
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Extract narration text from final script for Semantic Text Binding.")
    parser.add_argument("--input", default="data/final_script_with_narration.json", help="Input script path")
    parser.add_argument("--output", default="data/narration_only.json", help="Output path for narration text")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[extract_narration] ERROR: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
        
    print(f"[extract_narration] 로드 중: {args.input}", file=sys.stderr)
    with open(args.input, "r", encoding="utf-8") as f:
        script = json.load(f)
        
    extracted_data = {}
    
    # scenes 배열 순회
    for scene in script.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        for block in scene.get("blocks", []):
            block_id = block.get("block_id")
            if not block_id:
                continue
            
            # 1. 나레이션 (필수 필드)
            narration = block.get("narration", "").strip()
            if not narration:
                continue
            
            # 기본 구조체 생성 (scene_id + narration)
            block_entry = {
                "scene_id": scene_id,
                "narration": narration
            }
            
            # 2. 증거 인용문 (선택적 필드 - 존재할 때만 포함)
            evidence_quotes = block.get("evidence_quotes", [])
            quotes = [
                eq["text"].strip()
                for eq in evidence_quotes
                if isinstance(eq, dict) and eq.get("text")
            ]
            if quotes:
                # quotes 키는 인용구가 있을 때만 추가 (없으면 키 자체 생략)
                block_entry["quotes"] = quotes
            
            extracted_data[block_id] = block_entry
                
    # 디렉토리 생성 및 저장
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
    print(f"[extract_narration] SUCCESS: {len(extracted_data)}개의 나레이션 블록 추출 -> {args.output}")

if __name__ == "__main__":
    main()
