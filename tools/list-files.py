import boto3, sys

session = boto3.Session()
s3 = session.resource('s3')
bucket = s3.Bucket('gale8-uk')

for obj in bucket.objects.all():
    print(obj.key)
