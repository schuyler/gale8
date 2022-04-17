import os, logging, io, json, re
import boto3
from botocore.exceptions import ClientError

def get_config():
    return {
        "bucket": "gale8-uk",
        "cue_prefix": "cues/",
        "catalog": "archive/catalog.json",
        "broadcast_times": ["0048", "0520", "1201", "1754"]
    }

def set_log_level():
    # https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
    logging.getLogger().setLevel(logging.INFO)

def in_production():
    return os.environ.get("AWS_EXECUTION_ENV") is not None

def download_json(bucket, key):
    logging.info(f"Downloading {key} from {bucket.name}")
    data = None
    try:
        buffer = io.BytesIO()
        bucket.download_fileobj(key, buffer)
        buffer.seek(0)
        data = json.load(buffer)
    except ClientError as e:
        logging.info(f"Can't find {key}: {e}")
    return data

def upload_json(bucket, key, data):
    logging.info(f"Uploading {key} to {bucket.name}")
    buffer = io.BytesIO(json.dumps(data).encode("utf-8"))
    if not in_production():
        logging.info("(not running in production, so not actually uploading)")
        return
    bucket.upload_fileobj(buffer, key, ExtraArgs={"ACL": "public-read"})

def handle_event(event, context):
    set_log_level()

    config = get_config()
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(config["bucket"])

    file = event["file"]
    logging.info(f"Attempting to catalog {file}")

    if "cues" not in event:
        cue_file = cue_prefix + os.path.basename(mp3_file) + ".json"
        cues = download_json(bucket, cue_file)
    else:
        cues = event["cues"]

    catalog = download_json(bucket, config["catalog"])
    if not catalog:
        logging.error(f"Can't read catalog file {catalog}")
        return

    if cues and "shipping" not in cues and "forecast" not in cues:
        logging.info(f"Can't identify start time of broadcast from cues; skipping catalog")
        return

    m = re.match(r'.*\b(....)(..)(..)Z(....).mp3$', file)
    if not m:
        logging.error(f"File {file} doesn't match naming format")
        return

    year, month, day, timing = m.groups()
    if timing not in config["broadcast_times"]:
        logging.info(f"Start time {timing} doesn't match a broadcast time; skipping catalog")
        return

    catalog.setdefault(year, {}) \
           .setdefault(month, {}) \
           .setdefault(day, []) \
           .append(timing)

    upload_json(bucket, config["catalog"], catalog)

if __name__ == "__main__":
    import sys
    file = sys.argv[1]
    cues = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    handle_event({"file": file, "cues": cues}, {})
