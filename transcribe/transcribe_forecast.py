import sys, os, time, subprocess, json, tempfile, logging
import boto3
from botocore.exceptions import ClientError
from vosk import Model, KaldiRecognizer, SetLogLevel
from urllib import parse

SetLogLevel(-1)

sample_rate = 16000
bytes_per_sample = sample_rate * 2
window_size = bytes_per_sample // 4
triggers = {"shipping": 0.625, "forecast": 0.625, "bulletin": 0.625, "bbc": 0.5, "radio": 0.5}

def get_config():
    return {
        "bucket": "gale8-uk",
        "prefix": "cues"
    }

def set_log_level():
    # https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
    logging.getLogger().setLevel(logging.INFO)

def in_production():
    return os.environ.get("AWS_EXECUTION_ENV") is not None

def recognizer(model_path="/opt/model"):
    model = Model(model_path)
    rec = KaldiRecognizer(model, sample_rate)
    return rec

def detect(rec, filename):
    if not os.path.exists(filename):
        raise Error(f"{filename} not found")

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
    return {
        "file": basename,
        "cues": cues,
        "transcript": lines,
        "length": round(bytes_read / float(bytes_per_sample), 3)
    }

def start_catalog(file, event):
    lambda_ = boto3.client('lambda')
    logging.info(f"Initiating catalog of {file}")
    lambda_.invoke(
        FunctionName="catalog-forecast",
        InvocationType="Event",
        Payload=json.dumps(event)
    )

def handle_event(event, context):
    set_log_level()
    config = get_config()
    bucket = config["bucket"]
    s3 = boto3.client("s3")
    work_dir = tempfile.TemporaryDirectory()
    logging.info(f"Instantiating speech recognizer")
    model_path = event.get("model", "/opt/model")
    rec = recognizer(model_path)
    cues = {}
    for mp3_file in event["files"]:
        filename = os.path.join(work_dir.name, os.path.basename(mp3_file))
        logging.info(f"Fetching {mp3_file} from {bucket} to {filename}")
        s3.download_file(config["bucket"], mp3_file, filename)
        logging.info(f"Extracting transcript from {filename}")
        data = detect(rec, filename)
        cue_filename = filename + ".json"
        logging.info(f"Writing transcript to {cue_filename}")
        with open(cue_filename, "w") as cue_file:
           json.dump(data, cue_file)
        object_name = config["prefix"] + "/" + os.path.basename(cue_filename)
        logging.info(f"Uploading {cue_filename} to s3://{bucket}/{object_name}")
        if in_production():
            s3.upload_file(cue_filename, bucket, object_name, ExtraArgs={'ACL': 'public-read'})
            if not event.get("skip_catalog"):
                start_catalog(mp3_file, data) # probably not a race condition?
        else:
            logging.info("(not running in production, so not uploading)")
        cues[mp3_file] = data
    return cues

def handle_batch_event(event, context):
    set_log_level()
    config = get_config()
    invocation_id = event['invocationId']
    invocation_schema_version = event['invocationSchemaVersion']
    results = []

    for task in event['tasks']:
        task_id = task['taskId']
        result_code = None
        result_string = None

        try:
            obj_key = parse.unquote(task['s3Key'], encoding='utf-8')
            # bucket_name = task['s3BucketArn'].split(':')[-1]
            logging.info("Got task: transcribe %s", obj_key)
            output = handle_event({"files": [obj_key], "skip_catalog": True}, context)
            cues = output[obj_key]["cues"]
            length = output[obj_key]["length"]
            timings = cues.get("shipping", []) + cues.get("forecast", []) + [length]
            result_code = 'Succeeded'
            result_string = ",".join(map(str, timings))
        except Exception as error:
            result_code = 'PermanentFailure'
            result_string = str(error)
            logging.exception(error)
        finally:
            results.append({
                'taskId': task_id,
                'resultCode': result_code,
                'resultString': result_string
            })

    return {
        'invocationSchemaVersion': invocation_schema_version,
        'treatMissingKeysAs': 'PermanentFailure',
        'invocationId': invocation_id,
        'results': results
    }

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "-s":
        result = handle_batch_event({
            "invocationId": "test-run",
            "invocationSchemaVersion": "0.01",
            "tasks": [{ "taskId": "1", "s3Key": sys.argv[2] }],
            "model": "../detection/model"
            }, {})
        print(result)
    else:
        handle_event({"files": sys.argv[1:], "model": "../detection/model"})
