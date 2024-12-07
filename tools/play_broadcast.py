import boto3
import subprocess
import sys
from datetime import datetime

def play_broadcast(date_str, time_str):
    """Downloads and plays a broadcast for a given date and time.

    Args:
        date_str: The date in the format yyyymmdd.
        time_str: The time in the format HHMM.
    """
    try:
        date_time_str = date_str + "Z" + time_str
        date_time = datetime.strptime(date_time_str, "%Y%m%dZ%H%M")
    except ValueError:
        print("Invalid date or time format. Use yyyymmdd for date and HHMM for time.")
        return

    filename = date_time.strftime("%Y%m%dZ%H%M.mp3")
    s3 = boto3.client('s3')
    bucket_name = 'gale8-uk'
    object_key = 'archive/' + filename

    try:
        s3.head_object(Bucket=bucket_name, Key=object_key)
    except Exception as e:
        print(f"Broadcast not found: {filename}")
        return

    with open(filename, 'wb') as f:
        s3.download_fileobj(bucket_name, object_key, f)

    try:
        subprocess.run(['ffplay', '-nodisp', '-autoexit', filename], check=True)
    except subprocess.CalledProcessError:
        print("Could not play the broadcast. Ensure you have ffplay installed.")
    finally:
        subprocess.run(['rm', filename])

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python play_broadcast.py <date> <time>")
        print("Example: python play_broadcast.py 20240415 0520")
        sys.exit(1)

    date_str = sys.argv[1]
    time_str = sys.argv[2]
    play_broadcast(date_str, time_str)
