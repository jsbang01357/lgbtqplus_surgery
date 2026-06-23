import os
import time
import logging
from pathlib import Path
from google.cloud import storage

# 보류된 parser-core/GCS sync 실험용 스크립트입니다.
# 현재 Qplus Surgery 오프라인 운영 경로에서는 사용하지 않습니다.

# --- Configuration ---
# You can set these environment variables or edit them here.
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "lgbtqplus-surgery")
SYNC_ROOT = Path(os.path.expanduser(os.getenv("LOCAL_SYNC_ROOT", "~/Developer/qplus_surgery_workspace"))).expanduser()
STAGING_PREFIX = os.getenv("V6_STAGING_PREFIX", "v6_sync")
POLL_INTERVAL = int(os.getenv("SYNC_POLL_INTERVAL", "10"))
SERVICE_ACCOUNT_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "") # Path to .json file

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("v6-sync-daemon")

def get_storage_client():
    if SERVICE_ACCOUNT_JSON and os.path.exists(SERVICE_ACCOUNT_JSON):
        return storage.Client.from_service_account_json(SERVICE_ACCOUNT_JSON)
    return storage.Client()

def sync_v6_artifacts():
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    
    logger.info(f"Checking for new artifacts in gs://{GCS_BUCKET_NAME}/{STAGING_PREFIX}...")
    
    blobs = bucket.list_blobs(prefix=STAGING_PREFIX)
    downloaded_count = 0
    
    for blob in blobs:
        if blob.name.endswith("/"): # Skip directory blobs
            continue
            
        # The path structure in GCS is v6_staging/patient_id/kind/filename
        # We want to mirror this under SYNC_ROOT/patient_id/kind/filename
        relative_path = blob.name[len(STAGING_PREFIX):].lstrip("/")
        local_path = SYNC_ROOT / relative_path
        
        # Ensure parent directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simple sync logic: download if local file doesn't exist or size/mtime differs
        # For a more robust version, we'd use content hashes.
        if local_path.exists():
            local_stat = local_path.stat()
            if local_stat.st_size == blob.size:
                # logger.debug(f"Skipping {relative_path} (already up to date)")
                continue
        
        logger.info(f"Downloading {relative_path} -> {local_path}")
        blob.download_to_filename(str(local_path))
        downloaded_count += 1
        
    if downloaded_count > 0:
        logger.info(f"Successfully downloaded {downloaded_count} new/updated artifacts.")
    else:
        logger.info("No new artifacts found.")

def main():
    logger.info("Starting V6 Sync Daemon...")
    logger.info(f"Local Workspace: {SYNC_ROOT}")
    logger.info(f"GCS Staging: gs://{GCS_BUCKET_NAME}/{STAGING_PREFIX}")
    
    SYNC_ROOT.mkdir(parents=True, exist_ok=True)
    
    try:
        while True:
            try:
                sync_v6_artifacts()
            except Exception as e:
                logger.error(f"Sync error: {e}")
                
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")

if __name__ == "__main__":
    main()
