import time, os, logging, tempfile
import boto3
from urllib.request import urlopen
from botocore.exceptions import ClientError

def get_config():
    return {
        # https://gist.github.com/bpsib/67089b959e4fa898af69fea59ad74bc3
        "stream": os.environ["FORECAST_STREAM"],
        "bucket": "gale8-uk",
        "prefix": "archive/"
    }

def download_stream(stream, target, secs, block_size=1<<13):
    start = time.time()
    try:
        logging.info(f"downloading {stream} for {secs} s")
        with urlopen(stream) as source:
            while time.time() - start < secs:
                block = source.read(block_size)
                if not block: break
                target.write(block)
    except Exception as e:
        logging.error(e)
        return False
    return True

def upload_file(filename, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(filename)
    s3_client = boto3.client('s3')
    extra_args={'ACL': 'public-read'}
    try:
        logging.info(f"uploading {filename} to s3://{bucket}/{object_name}")
        response = s3_client.upload_file(filename, bucket, object_name, ExtraArgs=extra_args)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def generate_file_name():
    return time.strftime("%Y%m%dZ%H%M") + '.mp3'

def wait_until(hour, minute):
    mark = time.localtime()
    if mark.tm_hour == hour and mark.tm_min == minute:
        return
    delay = ((hour - mark.tm_hour) * 60 + minute - mark.tm_min) * 60 - mark.tm_sec
    if delay > 0:
        logging.info(f"waiting {delay} sec until {hour}:{minute}")
        time.sleep(delay)

def record_stream(stream, bucket, prefix, duration, hour=0, minute=0):
    if hour or minute:
        wait_until(hour, minute)
    with tempfile.NamedTemporaryFile() as temp:
        if download_stream(stream, temp, duration):
            filename = generate_file_name()
            upload_file(temp.name, bucket, prefix + filename)

def handle_lambda_event(event, context):
    # https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
    logging.getLogger().setLevel(logging.INFO)
    duration = int(event.get("duration", 12*60))
    hour, minute = 0, 0
    if "time" in event:
        try:
            hour, minute = map(int, event["time"].split(":"))
        except Exception as e:
            logging.error(e)
            pass
    config = get_config()
    record_stream(config["stream"], config["bucket"], config["prefix"],
                  duration, hour, minute)

if __name__ == "__main__":
    handle_lambda_event({"duration": 5}, {})
