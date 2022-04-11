#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys, os, time
import subprocess, multiprocessing, json

SetLogLevel(-1)

if not os.path.exists("model"):
    print ("Model expected in model/")
    exit (1)

sample_rate = 16000
bytes_per_sample = sample_rate * 2
window_size = bytes_per_sample // 4

triggers = {"shipping": 0.625, "forecast": 0.625, "bulletin": 0.625, "bbc": 0.5, "radio": 0.5}
model = rec = None
output_path = ""

def get_model(output):
    print(f"greetings from #{os.getpid()}", file=sys.stderr)
    global model, rec, output_path
    if model or rec:
        raise("model or rec was already initialized")
    model = Model("model")
    rec = KaldiRecognizer(model, sample_rate)
    output_path = output

def detect(filename):
    if not os.path.exists(filename):
        return ("", [])

    process = subprocess.Popen(
            ['ffmpeg', '-loglevel', 'quiet', '-i',
            filename,
            '-ar', str(sample_rate) , '-ac', '1', '-f', 's16le', '-'],
            stdout=subprocess.PIPE)

    cues = {}
    seen = {}
    lines = []
    start = time.time()
    bytes_read = line_start = 0

    rec.Reset()
    while True:
        data = process.stdout.read(window_size)
        if len(data) == 0:
            break
        complete = rec.AcceptWaveform(data)
        if complete:
            result = rec.Result()
            parsed = json.loads(result)
            text = parsed.get("text")
            if text:
                lines.append([round(line_start, 3), text])
        else:
            result = rec.PartialResult()
        for trigger, cue_latency in triggers.items():
            if trigger in seen: continue
            if trigger in result:
                cues.setdefault(trigger, [])
                cue_start = bytes_read / float(bytes_per_sample) - cue_latency
                cues[trigger].append(round(cue_start, 3))
                seen[trigger] = True
        bytes_read += len(data)
        if complete:
            line_start = bytes_read / bytes_per_sample
            seen = {}

    basename = os.path.basename(filename)
    with open(f"{output_path}/{basename}.json", "w") as f:
        json.dump({
            "file": basename,
            "cues": cues,
            "transcript": lines,
            "length": round(bytes_read / float(bytes_per_sample), 3)
        }, f)

    print("{} {} ({:.2f}s elapsed)".format(filename, cues, time.time() - start), file=sys.stderr)
    return (filename, cues)

if __name__ == "__main__":
    output_path = sys.argv[1]
    files = sys.argv[2:]
    if not output_path or not files:
        raise Error(f"Usage: {sys.argv[0]} <output_path> <files>...")
    with multiprocessing.Pool(processes=6, initializer=get_model, initargs=(output_path,)) as p:
        for filename, cues in p.map(detect, files):
            print(filename, cues)
