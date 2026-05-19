import io
import json
import logging
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

from app.config import get_bucket_name, get_gdrive_folder_id
from app.gcs_helper import get_bucket

logger = logging.getLogger(__name__)

# --- Configuration ---
SYNC_INTERVAL = 300  # 5 minutes
GDRIVE_TOKEN_BLOB = "auth/gdrive_token.json"

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
            # Check if token needs refresh (discovery build handles some of this, 
            # but we should ideally refresh if expired)
            return self._drive_service
        
        try:
            bucket = get_bucket()
            blob = bucket.blob(GDRIVE_TOKEN_BLOB)
            if not blob.exists():
                logger.warning("Google Drive OAuth token not found in GCS. Sync disabled.")
                return None
            
            token_data = json.loads(blob.download_as_text())
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # Discovery build will use the credentials and automatically refresh if needed 
            # (if refresh_token is present)
            self._drive_service = build("drive", "v3", credentials=creds)
            return self._drive_service
        except Exception as e:
            logger.error(f"Failed to initialize Drive API via OAuth2: {e}")
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

        logger.info("Starting GCS to Drive sync (OAuth2)...")
        bucket = get_bucket()
        blobs = bucket.list_blobs()
        
        sync_count = 0
        for blob in blobs:
            if blob.name.endswith("/") or blob.name.startswith("auth/"):
                continue

            path_parts = blob.name.split("/")
            file_name = path_parts.pop()
            parent_id = self._get_or_create_folder(path_parts) if path_parts else self.folder_id

            # Check if file exists and compare size
            query = f"name = '{file_name}' and '{parent_id}' in parents and trashed = false"
            try:
                results = service.files().list(q=query, fields='files(id, md5Checksum, size)').execute()
                drive_files = results.get('files', [])
            except Exception as e:
                logger.error(f"Failed to list files in Drive for {blob.name}: {e}")
                continue

            needs_upload = True
            drive_file_id = None
            if drive_files:
                drive_file = drive_files[0]
                drive_file_id = drive_file['id']
                if int(drive_file.get('size', 0)) == blob.size:
                    needs_upload = False

            if needs_upload:
                logger.info(f"Syncing {blob.name} to Drive...")
                try:
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
                except Exception as e:
                    logger.error(f"Failed to upload {blob.name} to Drive: {e}")

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
