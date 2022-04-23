import os
import logging
import io
import json
import random
import shutil
import boto3
import subprocess
from botocore.exceptions import ClientError

BYTES_PER_SEC = 1 << 13


def get_config():
    return {
        "bucket": "gale8-uk",
        "cue_prefix": "cues/",
        "mp3_prefix": "archive/",
        "catalog": "archive/catalog.json",
        "stream_key": "stream.mp3",
        "default_length": 45 * 60,
        "fade_secs": 5
    }


def set_log_level():
    # https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
    logging.getLogger().setLevel(logging.INFO)


def in_production():
    return os.environ.get("AWS_EXECUTION_ENV") is not None


def download_file(bucket, key):
    logging.info(f"Downloading {key} from {bucket.name}")
    try:
        buffer = io.BytesIO()
        bucket.download_fileobj(key, buffer)
        buffer.seek(0)
    except ClientError as e:
        logging.error(f"Can't download {key}: {e}")
    return buffer


def upload_file(bucket, key, fileobj):
    logging.info(f"Uploading {key} to {bucket.name}")
    # buffer = io.BytesIO(json.dumps(data).encode("utf-8"))
    if in_production():
        try:
            bucket.upload_fileobj(fileobj, key, ExtraArgs={
                                  "ACL": "public-read"})
        except ClientError as e:
            logging.error(f"Can't upload to {bucket}: {e}")
    else:
        logging.info("(Not running in production, so saving locally instead)")
        with open(os.path.basename(key), "wb") as output:
            shutil.copyfileobj(fileobj, output)


def download_json(bucket, key):
    buffer = download_file(bucket, key)
    return json.load(buffer)


def get_bucket(config):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(config["bucket"])
    return bucket


def get_random_file(catalog):
    def pick(x): return random.choice(list(x.keys()))
    yr = pick(catalog)
    mo = pick(catalog[yr])
    day = pick(catalog[yr][mo])
    timing = random.choice(catalog[yr][mo][day])
    return f"{yr}{mo}{day}Z{timing}.mp3"


def get_last_file(catalog):
    def pick(x): return list(sorted(x.keys()))[-1]
    yr = pick(catalog)
    mo = pick(catalog[yr])
    day = pick(catalog[yr][mo])
    timing = catalog[yr][mo][day][-1]
    return f"{yr}{mo}{day}Z{timing}.mp3"


def get_forecast_times(data, spacing_secs=5):
    duration = data["length"]
    start_boundary = (2.5 if duration > 5*60 else 1.5) * 60
    end_boundary = (5 if duration > 9*60 else 3) * 60
    cues = data["cues"]
    start = 0
    if "shipping" in cues:
        times = list(
            sorted(t for t in cues["shipping"] if t <= start_boundary))
        if times:
            start = times[-1]
    if not start and "forecast" in cues:
        times = list(
            sorted(t for t in cues["forecast"] if t <= start_boundary))
        if times:
            start = times[0]
    if start > spacing_secs:
        start -= spacing_secs
    end = duration
    for key in ("shipping", "bulletin", "bbc", "radio"):
        if key not in cues:
            continue
        times = list(sorted(t for t in cues[key] if t >= end_boundary))
        if times:
            end = times[0]
        if end:
            break
    if end + spacing_secs < duration:
        end += spacing_secs
    return (start, end)


def fade_audio_stream(data, start, end, fade_secs=5):
    # ffmpeg -ss 10 -to 25 -i - -b:a 128k -ac 1 -af "afade=t=in:st=0:d=5,afade=t=out:st=10:d=5" -f mp3 -
    logging.info(f"Re-encoding {end - start}s of MP3 audio")
    fade_start = end - start - fade_secs
    process = subprocess.Popen(
        ['ffmpeg', '-loglevel', 'error',
            # start n seconds into the stream
            '-ss', str(start),
            # stop n seconds into the stream
            '-to', str(end),
            # read from STDIN
            '-i', '-',
            # downmix to mono
            '-ac', '1',
            # set bitrate
            '-ab', '128k',
            # apply an audio filter to fade in and out
            '-af', f"afade=t=in:st=0:d={fade_secs},afade=t=out:st={fade_start}:d={fade_secs}",
            # output mp3 to STDOUT
            '-f', 'mp3', '-'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    output, err = process.communicate(data)
    process.wait()
    if process.returncode != 0:
        logging.error(f"ffmpeg returned {process.returncode}: {err}")
    return output

def handle_event(event, context):
    set_log_level()
    config = get_config()
    bucket = get_bucket(config)
    catalog = download_json(bucket, config["catalog"])
    stream_secs = int(event["length"]) if "length" in event else config["default_length"]
    stream = io.BytesIO()
    file = get_last_file(catalog)
    while len(stream.getvalue()) < stream_secs * BYTES_PER_SEC:
        cue_data = download_json(bucket, config["cue_prefix"] + file + ".json")
        start, end = get_forecast_times(cue_data)
  
        logging.info(f"Truncating {file} from {start}s to {end}s")

        audio = download_file(bucket, config["mp3_prefix"] + file)
        faded_audio = fade_audio_stream(audio.getvalue(), start, end, config["fade_secs"])
        stream.write(faded_audio)

        #shutil.copyfileobj(audio, stream)
        file = get_random_file(catalog)
    stream.seek(0)
    upload_file(bucket, config["stream_key"], stream)


if __name__ == "__main__":
    handle_event({}, {})
