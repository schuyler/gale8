import boto3
from botocore.exceptions import ClientError

def update_mp3_content_types(bucket_name, prefix=''):
    """
    Walk through an S3 bucket, find MP3 files, and ensure correct content type.
    
    Args:
        bucket_name (str): Name of the S3 bucket
        prefix (str): Optional prefix/folder path to start from
    """
    s3_client = boto3.client('s3')
    
    # Use paginator to handle buckets with many objects
    paginator = s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            
            # Check if file has .mp3 extension
            if not key.lower().endswith('.mp3'):
                continue
                
            try:
                # Get current object metadata
                response = s3_client.head_object(Bucket=bucket_name, Key=key)
                current_content_type = response.get('ContentType', '')
                
                # Update if content type is not already audio/mpeg
                if current_content_type != 'audio/mpeg':
                    print(f"Updating content type for {key} ({current_content_type})")
                    s3_client.copy_object(
                        Bucket=bucket_name,
                        CopySource={'Bucket': bucket_name, 'Key': key},
                        Key=key,
                        MetadataDirective='REPLACE',
                        ContentType='audio/mpeg',
                        ACL='public-read',
                        Metadata=response.get('Metadata', {})
                    )
                else:
                    print(f"Correct content type already set for {key}")
                    
            except ClientError as e:
                print(f"Error processing {key}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Replace with your bucket name and optional prefix
    BUCKET_NAME = "gale8-uk"
    PREFIX = "archive/"  # Optional: specify a folder path
    
    update_mp3_content_types(BUCKET_NAME, PREFIX)