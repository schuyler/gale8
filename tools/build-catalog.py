import boto3, sys, re, json

session = boto3.Session()
s3 = session.resource('s3')
bucket = s3.Bucket('gale8-uk')

prefix = "archive"
filename = re.compile(f".*{prefix}/(....)(..)(..)Z(....).mp3$")
catalog = {}

for obj in bucket.objects.all():
    m = filename.match(obj.key)
    if not m:
        print('failed:', obj.key, file=sys.stderr)
        continue
    year, month, day, timing = m.groups()
    catalog.setdefault(year, {}) \
           .setdefault(month, {}) \
           .setdefault(day, []) \
           .append(timing)

with open("catalog.json", "w") as f:
    json.dump(catalog, f)
