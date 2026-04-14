import wave
import json
import os

def merge_wavs(file_list, output_file):
    data = []
    for infile in file_list:
        if not os.path.exists(infile):
            print(f"File not found: {infile}")
            continue
        with wave.open(infile, 'rb') as w:
            data.append([w.getparams(), w.readframes(w.getnframes())])
        
    if not data:
        print("No audio data to merge.")
        return

    with wave.open(output_file, 'wb') as output:
        output.setparams(data[0][0])
        for i in range(len(data)):
            output.writeframes(data[i][1])

if __name__ == "__main__":
    script_path = 'data/script_output.json'
    if not os.path.exists(script_path):
        print("Script file not found: ", script_path)
        exit(1)
        
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)
        
    blocks = [block['block_id'] for scene in script['scenes'] for block in scene['blocks']]
    files = [f"data/narration_audio/{bid}.wav" for bid in blocks]
    
    out_file = 'data/merged_narration.wav'
    merge_wavs(files, out_file)
    print(f"Successfully merged {len(files)} files into {out_file}")
