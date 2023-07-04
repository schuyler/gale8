# Install prereqs

```
apt-get install sox ffmpeg
pip install -r requirements.txt
```

# Configure Vosk

```
wget -Omodel.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip model.zip
mv vosk-model* model
rm -f model.zip
```
