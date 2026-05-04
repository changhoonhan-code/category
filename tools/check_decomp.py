import json

with open('data/raw_draft.md', encoding='utf-8') as f:
    raw = f.read()

with open('data/draft_script.json', encoding='utf-8') as f:
    script = json.load(f)

total_blocks = 0
empty_blocks = []
probes_missing = []

raw_clean = raw.replace('*', '')

for scene in script['scenes']:
    for block in scene['blocks']:
        total_blocks += 1
        n = block['narration']
        if not n.strip():
            empty_blocks.append(block['block_id'])
        # Use first 80 chars stripped of markdown as probe
        probe = n.strip()[:80].replace('*', '')
        if probe not in raw_clean:
            probes_missing.append((block['block_id'], probe[:60]))

print(f"Total blocks: {total_blocks}")
print(f"Empty blocks: {empty_blocks if empty_blocks else 'None'}")
print(f"Narration probes missing from raw: {probes_missing if probes_missing else 'None'}")

# Verify total narration character coverage (rough)
combined = ' '.join(b['narration'] for s in script['scenes'] for b in s['blocks'])
print(f"Total narration chars in script: {len(combined)}")
print(f"Raw draft content chars (approx): {len(raw)}")
print("PASS" if not empty_blocks and not probes_missing else "FAIL")
