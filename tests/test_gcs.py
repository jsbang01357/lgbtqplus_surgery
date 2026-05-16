import sys
import os
sys.path.append(os.getcwd())

from app.gcs_helper import get_gcs_client, get_bucket
try:
    bucket = get_bucket()
    print("Bucket name:", bucket.name)
    print("Files in bucket:")
    for b in list(bucket.list_blobs(max_results=5)):
        print(" -", b.name)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

