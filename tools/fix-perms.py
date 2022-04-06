import boto3, sys

session = boto3.Session()
s3 = session.resource('s3')
bucket = s3.Bucket('gale8-uk')

for obj in bucket.objects.all():
    acl = obj.Acl()
    if not any(g for g in acl.grants if g["Permission"] == "READ"):
        print(obj.key, file=sys.stderr)
        acl.put(ACL='public-read')
