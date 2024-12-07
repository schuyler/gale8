import boto3
import sys

def delete_files(bucket_name, mp3_filenames):
    """Deletes MP3 files and their corresponding JSON cue files from S3."""
    session = boto3.Session()
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    for mp3_filename in mp3_filenames:
        # Delete MP3 file
        mp3_key = f"archive/{mp3_filename}"
        bucket.delete_objects(Delete={'Objects': [{'Key': mp3_key}]})
        print(f"Deleted: s3://{bucket_name}/{mp3_key}")

        # Delete corresponding JSON cue file
        json_key = f"cues/{mp3_filename.replace('.mp3', '.json')}"
        bucket.delete_objects(Delete={'Objects': [{'Key': json_key}]})
        print(f"Deleted: s3://{bucket_name}/{json_key}")

if __name__ == "__main__":
    bucket_name = 'gale8-uk'
    mp3_filenames = [line.strip() for line in sys.stdin if line]
    delete_files(bucket_name, mp3_filenames)
