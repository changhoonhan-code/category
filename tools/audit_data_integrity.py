import sys
import os
import json
import re

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add the project root to sys.path to allow importing from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.config import DATAS_DIR

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_numbers(text):
    return set(re.findall(r'\d[\d,]*\.?\d*', text))

def get_block_dict(script_data):
    blocks = {}
    for scene in script_data.get('scenes', []):
        for block in scene.get('blocks', []):
            blocks[block['block_id']] = block.get('narration', '')
    return blocks

def main():
    draft_path = os.path.join(DATAS_DIR, 'draft_narration.json')
    output_path = os.path.join(DATAS_DIR, 'script_output.json')
    
    if not os.path.exists(draft_path):
        print(f"Error: {draft_path} not found.")
        sys.exit(1)
        
    # If script_output.json doesn't exist, we can't diff
    if not os.path.exists(output_path):
        print(f"Output script {output_path} not found. Running self-diff for testing with draft_narration.json")
        output_path = draft_path
        
    draft_data = load_json(draft_path)
    output_data = load_json(output_path)
    
    draft_blocks = get_block_dict(draft_data)
    output_blocks = get_block_dict(output_data)
    
    print("============================================================")
    print("  DATA INTEGRITY AUDIT - Numeric Preservation Check")
    print("============================================================\n")
    
    violations = []
    
    for bid, draft_narr in draft_blocks.items():
        out_narr = output_blocks.get(bid)
        if not out_narr:
            continue
            
        draft_nums = extract_numbers(draft_narr)
        out_nums = extract_numbers(out_narr)
        
        removed = draft_nums - out_nums
        added = out_nums - draft_nums
        
        if removed:
            violations.append({
                'block_id': bid,
                'removed': removed,
                'added': added,
                'draft_text': draft_narr,
                'out_text': out_narr
            })
            
    if violations:
        for v in violations:
            print(f"FAIL: Block '{v['block_id']}'")
            print(f"  REMOVED: {', '.join(v['removed'])}")
            if v['added']:
                print(f"  ADDED:   {', '.join(v['added'])}")
            print(f"  Draft: {v['draft_text']}")
            print(f"  Output: {v['out_text']}")
            print("-" * 60)
            
        print(f"\nResult: FAIL ({len(violations)} blocks lost numeric data)")
        sys.exit(1)
    else:
        print("Result: PASS (No numeric data removed)")
        sys.exit(0)

if __name__ == '__main__':
    main()
