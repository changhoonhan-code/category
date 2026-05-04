import json
import codecs

try:
    with open('data/draft_script.json', 'r', encoding='mbcs') as f:
        data = f.read()
except UnicodeDecodeError:
    with open('data/draft_script.json', 'r', encoding='utf-16') as f:
        data = f.read()

# Replace if it hasn't been replaced
data = data.replace('"text":', '"narration":')

# Validate it's a valid JSON before saving
try:
    json.loads(data)
    with open('data/draft_script.json', 'w', encoding='utf-8') as f:
        f.write(data)
    print("Successfully fixed encoding and key name.")
except json.JSONDecodeError as e:
    print(f"JSON Decode Error: {e}")
