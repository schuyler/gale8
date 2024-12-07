import sys
import boto3
import botocore.exceptions
import boto3.exceptions

def move_file(s3, bucket_name, old_key, new_key):
    copy_source = {'Bucket': bucket_name, 'Key': old_key}
    s3.meta.client.copy(copy_source, bucket_name, new_key)
    s3.Object(bucket_name, old_key).delete()

def main(dry_run=False):
    session = boto3.Session()
    s3 = session.resource('s3')
    bucket_name = 'gale8-uk'
    
    for line in sys.stdin:
        filename, length = line.strip().split()
        mp3_key = f'archive/{filename}'
        json_key = f'cues/{filename}.json'
        broken_mp3_key = f'broken/{filename}'
        broken_json_key = f'broken/{filename[:-4]}.json'
        
        if dry_run:
            print(f"Dry run: Would move {filename} and corresponding cue file to broken/")
        else:
            try:
                move_file(s3, bucket_name, mp3_key, broken_mp3_key)
                move_file(s3, bucket_name, json_key, broken_json_key)
                print(f"Moved {filename} and corresponding cue file to broken/")
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    print(f"Not found: {filename}")
                else:
                    print(f"Error moving {filename}: {e}")
            except Exception as e:
                print(f"Error moving {filename}: {e}")

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    main(dry_run)