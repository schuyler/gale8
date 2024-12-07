import boto3
import json
from datetime import datetime, timezone

def get_expected_length(filename):
    """Returns the expected length in seconds for a given filename.

    Args:
        filename: The filename in the format yymmddZHHMM.mp3.

    Returns:
        The expected length in seconds.
    """
    try:
        # Extract HHMM from the filename
        hhmm = filename[-8:-4]

        if hhmm == "0048" or hhmm == "0520":
            return 720
        elif hhmm == "1754" or hhmm == "1201":
            return 360
        else:
            return 0  # Unknown broadcast time
    except (IndexError, ValueError):
        return 0  # Invalid filename format

def main():
    """Iterates through cue files and finds recordings shorter than expected."""
    session = boto3.Session()
    s3 = session.resource('s3')
    bucket = s3.Bucket('gale8-uk')
    prefix = 'cues/'
    start_date = datetime(2024, 4, 1, tzinfo=timezone.utc)

    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.key.endswith(".json"): # and obj.last_modified >= start_date:
            cue_file_content = json.loads(obj.get()['Body'].read().decode('utf-8'))
            if "length" in cue_file_content:
                length = cue_file_content["length"]
                filename = obj.key[:-5]  # Remove ".json"
                filename = filename[len(prefix):]  # Remove "cues/" prefix
                expected_length = get_expected_length(filename)

                if expected_length > 0 and length <= expected_length / 2:
                    print(filename + " " + str(length))

if __name__ == "__main__":
    main()
