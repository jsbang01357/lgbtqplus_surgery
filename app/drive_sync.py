import io
import logging
import threading
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

from app.config import get_bucket_name, get_gdrive_folder_id, get_secrets_dict
from app.gcs_helper import get_bucket

logger = logging.getLogger(__name__)

# --- Configuration ---
SYNC_INTERVAL = 300  # 5 minutes
SYNC_STATE_BLOB = "auth/drive_sync_state.json"

class GDriveSyncService:
    def __init__(self):
        self.folder_id = get_gdrive_folder_id()
        self.bucket_name = get_bucket_name()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._drive_service = None
        self._folder_cache = {} # path -> folder_id

    def _get_drive_service(self):
        if self._drive_service:
            return self._drive_service
        
        secrets = get_secrets_dict()
        sa_info = secrets.get("gcp_service_account")
        if not sa_info:
            logger.error("Service account info not found in secrets.")
            return None
        
        try:
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=["https://www.googleapis.com/auth/drive"]
            )
            self._drive_service = build("drive", "v3", credentials=creds)
            return self._drive_service
        except Exception as e:
            logger.error(f"Failed to initialize Drive API: {e}")
            return None

    def _get_or_create_folder(self, path_parts):
        service = self._get_drive_service()
        current_parent = self.folder_id
        current_path = ""

        for part in path_parts:
            current_path = f"{current_path}/{part}" if current_path else part
            if current_path in self._folder_cache:
                current_parent = self._folder_cache[current_path]
                continue

            # Check if folder exists in Drive
            query = f"name = '{part}' and '{current_parent}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])

            if files:
                folder_id = files[0]['id']
            else:
                # Create folder
                file_metadata = {
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [current_parent]
                }
                folder = service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
                logger.info(f"Created Drive folder: {current_path} ({folder_id})")

            self._folder_cache[current_path] = folder_id
            current_parent = folder_id

        return current_parent

    def sync_once(self):
        service = self._get_drive_service()
        if not service:
            return

        logger.info("Starting GCS to Drive sync...")
        bucket = get_bucket()
        blobs = bucket.list_blobs()
        
        # Get existing files in the root folder to compare
        # In a production environment, we'd use a state file or more efficient queries.
        # For now, we'll traverse and sync.
        
        sync_count = 0
        for blob in blobs:
            if blob.name.endswith("/") or blob.name == SYNC_STATE_BLOB:
                continue

            path_parts = blob.name.split("/")
            file_name = path_parts.pop()
            parent_id = self._get_or_create_folder(path_parts) if path_parts else self.folder_id

            # Check if file exists and compare MD5
            # Note: GCS md5_hash is base64 encoded, Drive md5Checksum is hex.
            # However, Drive API 'list' is expensive. Let's try to get the specific file.
            query = f"name = '{file_name}' and '{parent_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields='files(id, md5Checksum, size)').execute()
            drive_files = results.get('files', [])

            needs_upload = True
            drive_file_id = None
            if drive_files:
                drive_file = drive_files[0]
                drive_file_id = drive_file['id']
                # If size matches, we assume it's same for simplicity in this version
                # Better: compare MD5
                if int(drive_file.get('size', 0)) == blob.size:
                    needs_upload = False

            if needs_upload:
                logger.info(f"Syncing {blob.name} to Drive...")
                blob_data = blob.download_as_bytes()
                fh = io.BytesIO(blob_data)
                media = MediaIoBaseUpload(fh, mimetype=blob.content_type, resumable=True)
                
                if drive_file_id:
                    # Update existing file
                    service.files().update(fileId=drive_file_id, media_body=media).execute()
                else:
                    # Create new file
                    file_metadata = {'name': file_name, 'parents': [parent_id]}
                    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                
                sync_count += 1

        logger.info(f"GCS to Drive sync finished. Updated {sync_count} files.")

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.sync_once()
            except Exception as e:
                logger.exception(f"Error in Drive sync loop: {e}")
            
            if self._stop_event.wait(SYNC_INTERVAL):
                break

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="gdrive-sync", daemon=True)
        self._thread.start()
        logger.info("GDriveSyncService started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("GDriveSyncService stopped.")

_GDRIVE_SYNC_SERVICE = None

def get_gdrive_sync_service():
    global _GDRIVE_SYNC_SERVICE
    if _GDRIVE_SYNC_SERVICE is None:
        _GDRIVE_SYNC_SERVICE = GDriveSyncService()
    return _GDRIVE_SYNC_SERVICE

def start_gdrive_sync_service():
    service = get_gdrive_sync_service()
    service.start()
    return service
