import boto3, sys, re, json

session = boto3.Session()
s3 = session.resource('s3')
bucket = s3.Bucket('gale8-uk')

prefix = "archive"
broadcast_times = ("0048", "0520", "1201", "1754")
filename = re.compile(f".*{prefix}/(....)(..)(..)Z(....).mp3$")
catalog = {}

exclude = set()
if len(sys.argv) > 1:
    with open(sys.argv[1]) as exclude_file:
        for line in exclude_file:
            exclude.add(line.strip())

for obj in bucket.objects.filter(Prefix=f"{prefix}/"):
    m = filename.match(obj.key)
    if not m:
        print('no match:', obj.key, file=sys.stderr)
        continue
    if obj.key in exclude:
        print('excluded:', obj.key, file=sys.stderr)
        continue
    year, month, day, timing = m.groups()
    if timing not in broadcast_times:
        print('wrong time:', obj.key, file=sys.stderr)
        continue
    catalog.setdefault(year, {}) \
           .setdefault(month, {}) \
           .setdefault(day, []) \
           .append(timing)

with open("catalog.json", "w") as f:
    json.dump(catalog, f)
