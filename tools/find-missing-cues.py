import boto3
import json
from datetime import datetime, timezone

def check_for_keywords(cue_file_content):
    """Checks if a cue file contains any of the required keywords."""
    keywords = ["shipping", "forecast", "bbc", "radio"]
    if "cues" not in cue_file_content:
        return False
    cues = cue_file_content["cues"]
    for keyword in keywords:
        if keyword in cues:
            return True
    return False

def main():
    """Iterates through cue files and finds those missing required keywords."""
    session = boto3.Session()
    s3 = session.resource('s3')
    bucket = s3.Bucket('gale8-uk')
    prefix = 'cues/'
    start_date = datetime(2024, 4, 1, tzinfo=timezone.utc)

    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.key.endswith(".json") and obj.last_modified >= start_date:
            cue_file_content = json.loads(obj.get()['Body'].read().decode('utf-8'))
            if not check_for_keywords(cue_file_content):
                # Extract the {...}.mp3 part
                filename = obj.key[:-5]  # Remove ".json"
                filename = filename[len(prefix):] #Remove "cues/" prefix
                print(filename)

if __name__ == "__main__":
    main()
