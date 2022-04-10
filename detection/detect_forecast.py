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
limit = 0 #120

triggers = ("shipping",)
model = rec = None

def get_model():
    print(f"greetings from #{os.getpid()}", file=sys.stderr)
    global model, rec
    if model or rec:
        raise("model or rec was already initialized")
    model = Model("model")
    rec = KaldiRecognizer(model, sample_rate)

def detect(filename):
    if not os.path.exists(filename):
        return ("", [])

    process = subprocess.Popen(
            ['ffmpeg', '-loglevel', 'quiet', '-i',
            filename,
            '-ar', str(sample_rate) , '-ac', '1', '-f', 's16le', '-'],
            stdout=subprocess.PIPE)

    found = []
    start = time.time()
    bytes_read = 0
    seen = False

    rec.Reset()
    while True:
        data = process.stdout.read(window_size)
        if len(data) == 0:
            break
        complete = rec.AcceptWaveform(data)
        if complete:
            result = rec.Result()
        else:
            result = rec.PartialResult()
        if not seen and any(p for p in triggers if p in result):
            found.append(bytes_read / float(bytes_per_sample))
            seen = True
        if complete:
            #print(seen, result.replace("\n", " "))
            seen = False
        bytes_read += len(data)
        #if limit and (seen or bytes_read > limit * bytes_per_sample):
        #    break

    cues = [round(t - 0.625, 3) for t in found]
    with open(f"{filename}.json", "w") as f:
        json.dump({
            "file": os.path.basename(filename),
            "cues": cues,
            "length": round(bytes_read / float(bytes_per_sample), 3)
        }, f)

    print("{} {} ({:.2f}s elapsed)".format(filename, cues, time.time() - start), file=sys.stderr)
    return (filename, cues)

if __name__ == "__main__":
    with multiprocessing.Pool(processes=6, initializer=get_model) as p:
        for filename, cues in p.map(detect, sys.argv[1:]):
            if cues:
                #out = "shipping/" + os.path.basename(filename).replace(".mp3", ".wav")
                #print(f"sox {filename} {out} trim 0:{cues[-1] - 0.625:.2f} 1 rate {sample_rate}")
                print(filename, " ".join(map(str, cues)))
