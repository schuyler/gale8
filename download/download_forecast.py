import time
import os
import os.path
import logging
import tempfile
import json
import signal
import subprocess
import boto3
import pytz
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

london = pytz.timezone('Europe/London')


def get_config():
    return {
        # https://gist.github.com/bpsib/67089b959e4fa898af69fea59ad74bc3
        "stream": os.environ["FORECAST_STREAM"],
        "bucket": "gale8-uk",
        "prefix": "archive/"
    }


def set_log_level():
    # https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
    logging.getLogger().setLevel(logging.INFO)


def in_production():
    return os.environ.get("AWS_EXECUTION_ENV") is not None


def local_now():
    return datetime.now(london)


def download_stream(stream, target, secs):
    try:
        logging.info(f"downloading {stream} for {secs} s")
        # download *and* re-encode as MP3
        proc = subprocess.Popen(
            ['ffmpeg', '-loglevel', 'error',
                '-y',
                '-i', stream,
                '-f', 'mp3', target],
            shell=False)
        time.sleep(secs)
        proc.send_signal(signal.SIGINT)
        proc.wait()
        if proc.returncode != 0 and proc.returncode != 255:
            logging.error(f"ffmpeg returned {proc.returncode}")
    except Exception as e:
        logging.error(e)
        return False
    return True


def upload_file(filename, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(filename)
    s3_client = boto3.client('s3')
    extra_args = {'ACL': 'public-read'}
    try:
        logging.info(f"uploading {filename} to s3://{bucket}/{object_name}")
        if in_production():
            s3_client.upload_file(
                filename, bucket, object_name, ExtraArgs=extra_args)
        else:
            logging.info(f"(not running in production; upload skipped)")
    except ClientError as e:
        logging.error(e)
        return False
    return True


def generate_file_name():
    return local_now().strftime("%Y%m%dZ%H%M") + '.mp3'


def wait_until(hour, minute):
    now = local_now()
    start = london.localize(
        datetime(now.year, now.month, now.day, hour, minute))
    delay = (start - now).total_seconds()
    if delay > 0:
        logging.info(f"waiting {delay:.1f} sec until {hour:02d}:{minute:02d}")
        time.sleep(delay)


def record_stream(stream, bucket, prefix, duration):
    # Compute the filename at the minute we care about
    filename = generate_file_name()
    with tempfile.TemporaryDirectory() as tempdir:
        target = os.path.join(tempdir.name, filename)
        if download_stream(stream, target, duration):
            upload_file(target, bucket, prefix + filename)
            return prefix + filename
    return ""


def set_next_launch(hour, minute, test_date=None):
    now = test_date or local_now()
    tomorrow = now + timedelta(days=1)
    start = london.localize(
        datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
        - timedelta(minutes=1))
    if now.dst() != start.dst():
        logging.info(f"*** difference in DST detected for tomorrow! ***")
    start = start.astimezone(pytz.utc)  # Eventbridge schedules are in UTC!!!
    logging.info(f"setting next launch for {start.isoformat()}")
    if test_date:
        logging.info("(running in test mode, so not actually updating)")
        return
    try:
        events = boto3.client('events')
        events.put_rule(
            Name=f"download-forecast-{hour:02}{minute:02}",
            ScheduleExpression=f"cron({start.minute} {start.hour} ? * * *)")
    except ClientError as e:
        logging.error(e)


def start_transcription(file):
    lambda_ = boto3.client('lambda')
    logging.info(f"Initiating transcription of {file}")
    lambda_.invoke(
        FunctionName="transcribe-forecast",
        InvocationType="Event",
        Payload=json.dumps({"files": [file]})
    )


def handle_event(event, context):
    set_log_level()
    duration = int(event.get("duration", 12*60))
    try:
        hour, minute = map(int, event["time"].split(":"))
    except Exception as e:
        logging.error(e)
        return
    config = get_config()
    stream = event.get("stream", config["stream"])
    bucket, prefix = config["bucket"], config["prefix"]
    wait_until(hour, minute)
    recording = record_stream(stream, bucket, prefix, duration)
    if recording:
        start_transcription(recording)
    set_next_launch(hour, minute, event.get("test_date"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "-s":
        # Run `python3 download_forecast.py -s` to ensure that Eventbridge rules are DST aware
        set_log_level()
        when = None
        if len(sys.argv) > 2:
            when = london.localize(datetime.strptime(sys.argv[2], "%Y-%m-%d"))
        for h, m in ((0, 48), (5, 20), (12, 1), (17, 54)):
            set_next_launch(h, m, when)
    else:
        when = local_now() + timedelta(minutes=1)
        start = f"{when.hour:02}:{when.minute:02}"
        handle_event({"duration": 5, "time": start, "test_date": when}, {})
