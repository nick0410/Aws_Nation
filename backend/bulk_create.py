import csv, time
from aws_service import create_s3_bucket

results = []
with open('../uipath_workflow/35_buckets.csv', newline='') as f:
    for row in csv.DictReader(f):
        name = row['bucket_name'].strip()
        r = create_s3_bucket(
            bucket_name  = name,
            region       = row['region'].strip(),
            access_level = row['access_level'].strip(),
            versioning   = row['versioning'].strip().lower() == 'true',
            tags         = {},
            owner_email  = row['owner_email'].strip()
        )
        status = 'OK  ' if r['success'] else 'FAIL'
        msg    = r.get('bucket_url', r.get('error', ''))
        print(f'[{status}] {name:<42} {msg}')
        results.append((name, r['success']))
        time.sleep(0.3)

created = sum(1 for _, s in results if s)
failed  = sum(1 for _, s in results if not s)
print(f'\n=== DONE: {created} created, {failed} failed out of {len(results)} ===')
