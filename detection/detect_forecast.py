#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import os
import wave
import subprocess
import time

SetLogLevel(-1)

if not os.path.exists("model"):
    print ("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.")
    exit (1)

sample_rate=16000
model = Model("model")
rec = KaldiRecognizer(model, sample_rate)

process = subprocess.Popen(['ffmpeg', '-loglevel', 'quiet', '-i',
                            sys.argv[1],
                            '-ar', str(sample_rate) , '-ac', '1', '-f', 's16le', '-'],
                            stdout=subprocess.PIPE)

bytes_read = 0
found = False
start = time.time()

while bytes_read < sample_rate * 180:
    data = process.stdout.read(4000)
    bytes_read += len(data)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        result = rec.Result()
    else:
        result = rec.PartialResult()
    if "shipping" in result:
        found = True
        break

if found:
    print("{:.2f}s".format(bytes_read / sample_rate))
print("elapsed: {:.2f}s".format(time.time() - start))
