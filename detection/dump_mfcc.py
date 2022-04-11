import librosa
import python_speech_features
import sys, json, os

files = sys.argv[1:]
feats = {}
for filename in files:
    y, sr = librosa.load(filename, sr=None)
    #mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=24).T
    mfcc = python_speech_features.mfcc(y, sr)
    key = os.path.basename(filename)
    feats[key] = mfcc.tolist()

json.dump(feats, sys.stdout)
