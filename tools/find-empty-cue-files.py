# Python script that parses each JSON file in the cues/ directory and prints out the file name if the "cues" object in the JSON blob is missing or empty.

import json, os

for filename in sorted(os.listdir('cues/')):
    if filename.endswith('.json'):
        with open(f'cues/{filename}') as f:
            data = json.load(f)
            if not data.get('cues'):
                print(filename)