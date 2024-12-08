import time
import os
import os.path
import logging
import tempfile
import json
import signal
import subprocess
import traceback
import boto3
import pytz
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import select

london = pytz.timezone('Europe/London')

broadcast_times = (
    (0, 48, "*"),
    (5, 20, "*"),
    (17, 54, "1,7")
)

def get_config():
    return {
        # https://gist.github.com/bpsib/67089b959e4fa898af69fea59ad74bc3
        "stream": os.environ["FORECAST_STREAM"],
        "notify": os.environ["ERROR_TOPIC_ARN"],
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

def notify(msg):
    if not in_production():
        return
    sns = boto3.resource("sns")
    arn = get_config()["notify"]
    topic = sns.Topic(arn)
    hour_min = local_now().strftime("%H:%M")
    topic.publish(
        Subject=f"[{hour_min}] download_forecast: {str(msg)}",
        Message=traceback.format_exc()
    )

def download_stream_segment(stream, target):
    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'info',
        '-reconnect', '1',
        # Can't use this because we're downloading an m3u8 playlist
        # https://medium.com/intrasonics/robust-continuous-audio-recording-c1948895bb49
        # '-reconnect_at_eof', '1',
        '-reconnect_on_network_error', '1',
        '-reconnect_on_http_error', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '10',
        '-i', stream,
        '-bufsize', '8192k',
        '-f', 'mp3',
        target
    ]

    logging.info(f"executing {' '.join(ffmpeg_cmd)}")
    proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            shell=False
        )
    return proc 

def download_stream(stream, target, secs):
    logging.info(f"downloading {stream} for {secs} s")

    start_time = time.time()
    end_time = start_time + secs
    segment_number = 0
    max_segments = 20

    # Loop until the end time is reached
    while time.time() < end_time and segment_number < max_segments:
        logging.info(f"downloading segment {segment_number}")
        proc = download_stream_segment(stream, f"{target}.{segment_number:03d}")
        output, errs = None, None
        try:
            output, errs = proc.communicate(timeout=end_time - time.time())
        except subprocess.TimeoutExpired:
            pass
        if output:
            logging.info("ffmpeg output: {output}")
        if errs:
            logging.warning("ffmpeg error: {errs}")
        if proc.poll() is None:
            logging.info("terminating ffmpeg process")
            proc.terminate()
            proc.wait()
        if proc.returncode not in (0, 255):
            stderr_output = proc.stderr.read()
            logging.error(f"ffmpeg failed with return code {proc.returncode}. Error: {stderr_output}\n")
        # Start a new segment
        segment_number += 1

    # Take all of the target segments and concatenate them
    with open(target, 'wb') as f:
        for i in range(segment_number):
            segment = f"{target}.{i:03d}"
            with open(segment, 'rb') as s:
                f.write(s.read())

    # Verify the output file exists and has content
    if not os.path.exists(target) or os.path.getsize(target) == 0:
        raise Exception("Output file is missing or empty")

    logging.info(f"downloaded {segment_number+1} segments to {target}")
    return True


def upload_file(filename, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(filename)
    s3_client = boto3.client('s3')
    extra_args = {'ACL': 'public-read'}
    logging.info(f"uploading {filename} to s3://{bucket}/{object_name}")
    if in_production():
        s3_client.upload_file(
            filename, bucket, object_name, ExtraArgs=extra_args)
        return True
    else:
        logging.info(f"(not running in production; upload skipped)")
        return False

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
        target = os.path.join(tempdir, filename)
        if download_stream(stream, target, duration) \
                and upload_file(target, bucket, prefix + filename):
            return prefix + filename
    return ""

def set_next_launch(test_date=None):
    now = test_date or local_now()
    tomorrow = now + timedelta(days=1)
    events = boto3.client('events')

    for hour, minute, days_of_week in broadcast_times:
        start = london.localize(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
            - timedelta(minutes=1))

        if now.dst() != start.dst():
            logging.info(f"*** difference in DST detected for tomorrow at {hour:02}:{minute:02}! ***")

        start = start.astimezone(pytz.utc)  # Eventbridge schedules are in UTC!!!
        rule_name = f"download-forecast-{hour:02}{minute:02}"
        cron_expr = f"cron({start.minute} {start.hour} ? * {days_of_week} *)"

        if not test_date:
            logging.info(f"setting launch for {rule_name} to {cron_expr}")
            events.put_rule(Name=rule_name, ScheduleExpression=cron_expr)
        else:
            logging.info(f"(not) setting launch for {rule_name} to {cron_expr}")


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
        config = get_config()
        stream = event.get("stream", config["stream"])
        bucket, prefix = config["bucket"], config["prefix"]
        wait_until(hour, minute)
        recording = record_stream(stream, bucket, prefix, duration)
        if recording:
            start_transcription(recording)
    except Exception as e:
        logging.exception("handle_event failure")
        notify("handle_event failure")
    try:
        set_next_launch(event.get("test_date"))
    except Exception as e:
        logging.exception("set_next_launch failure")
        notify("set_next_launch failure")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "-s":
        # Run `python3 download_forecast.py -s` to ensure that Eventbridge rules are DST aware
        set_log_level()
        when = None
        if len(sys.argv) > 2:
            when = london.localize(datetime.strptime(sys.argv[2], "%Y-%m-%d"))
        set_next_launch(when)
    else:
        when = local_now() + timedelta(minutes=1)
        start = f"{when.hour:02}:{when.minute:02}"
        handle_event({"duration": 5, "time": start, "test_date": when}, {})
