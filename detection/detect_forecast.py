#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import os
import wave
import subprocess
import time

SetLogLevel(-1)

if not os.path.exists("model"):
    print ("Model expected in model/")
    exit (1)

sample_rate=16000
model = Model("model")
rec = KaldiRecognizer(model, sample_rate)

process = subprocess.Popen(['ffmpeg', '-loglevel', 'quiet', '-i',
                            sys.argv[1],
                            '-ar', str(sample_rate) , '-ac', '1', '-f', 's16le', '-'],
                            stdout=subprocess.PIPE)

found = []
start = time.time()
bytes_read = 0
seen = False

while True:
    data = process.stdout.read(sample_rate)
    if len(data) == 0:
        break
    complete = rec.AcceptWaveform(data)
    if complete:
        result = rec.Result()
    else:
        result = rec.PartialResult()
    if "shipping" in result and not seen:
        found.append(bytes_read / sample_rate)
        seen = True
    if complete:
        print(seen, result.replace("\n", " "))
        seen = False
    bytes_read += len(data)

print([round(t, 2) for t in found])
print("elapsed: {:.2f}s".format(time.time() - start))
