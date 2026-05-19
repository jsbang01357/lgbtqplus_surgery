from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
import os
import secrets
from pathlib import Path
from dataclasses import asdict

from app.api_deps import _json, _file_response_bytes
from app.storage import create_zip_of_files, create_file_download_url, delete_uploaded_file, guess_content_type, list_uploaded_files_cached, list_uploaded_files, normalize_blob_name, MAX_UPLOAD_SIZE_BYTES, UPLOAD_PREFIX, download_file_bytes
from app.memo import load_memo_list_cached
from app.folder_sync import get_folder_sync_service
from app.gcs_helper import get_bucket
from app.core_utils import get_now

router = APIRouter()

@router.get('/api/sync/status')
async def folder_sync_status(request: Request):
    service = get_folder_sync_service()
    return _json(service.status())

@router.post('/api/sync/rescan')
async def folder_sync_rescan(request: Request):
    service = get_folder_sync_service()
    result = service.sync_now()
    return _json({"ok": True, **asdict(result)})

@router.get('/api/files')
async def files_list(request: Request):
    files = [
        {
            "name": item.name,
            "blob_name": item.blob_name,
            "size": item.size,
            "updated": item.updated.isoformat() if item.updated else "",
            "content_type": item.content_type or "",
            "download_url": create_file_download_url(item),
        }
        for item in list_uploaded_files()
    ]
    return _json({"files": files})

@router.get('/api/files/download')
async def files_download(request: Request):
    blob_name = request.query_params.get("blob_name")
    if not blob_name:
        return _json({"error": "blob_name is required"}, status_code=400)


    content, content_type, original_name = download_file_bytes(blob_name)
    return _file_response_bytes(content, original_name or blob_name, content_type)

@router.post('/api/files')
async def files_upload(request: Request):
    form = await request.form()
    uploaded = []
    bucket = get_bucket()
    for _, upload in form.multi_items():
        if not hasattr(upload, "filename"):
            continue

        filename = str(upload.filename or "")
        ext = Path(filename).suffix.lower()
        allowed_extensions = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
            ".txt",
            ".md",
            ".markdown",
            ".csv",
            ".docx",
            ".xlsx",
            ".pptx",
        }
        if ext not in allowed_extensions:
            return _json(
                {"error": f"지원하지 않는 파일 형식입니다 ({ext})."}, status_code=400
            )

        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            return _json(
                {"error": f"{upload.filename} 파일이 50MB 제한을 초과했습니다."},
                status_code=413,
            )
        safe_original = Path(upload.filename).name.replace("\\", "_").replace("/", "_")
        name = Path(safe_original).stem or "file"
        new_filename = safe_original
        blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        if bucket.blob(blob_name).exists():
            new_filename = f"{name}-{secrets.token_hex(3)}{ext}"
            blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        blob = bucket.blob(blob_name)
        content_type = upload.content_type or guess_content_type(upload.filename)
        blob.metadata = {
            "original_name": safe_original,
            "uploaded_at": get_now().isoformat(),
        }
        blob.upload_from_string(content, content_type=content_type)
        uploaded.append({"name": safe_original, "blob_name": blob_name})
    list_uploaded_files_cached.clear()
    create_zip_of_files.clear()
    return _json({"uploaded": uploaded})

@router.post('/api/files/delete')
async def files_delete(request: Request):
    payload = await request.json()
    delete_uploaded_file(payload.get("blob_name", ""))
    return _json({"ok": True})

@router.get('/api/files/zip')
async def files_zip(request: Request):
    
    zip_path = create_zip_of_files()
    if not zip_path or not os.path.exists(zip_path):
        return _json({"error": "다운로드할 파일이 없습니다."}, status_code=404)
        
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="jisong-cloud-files.zip",
        background=BackgroundTasks().add_task(os.remove, zip_path)
    )

@router.get('/api/files/content')
async def files_get_content(request: Request):
    
    blob_name = request.query_params.get("blob_name")
    if not blob_name:
        return _json({"error": "blob_name is required"}, status_code=400)
        
    try:
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return _json({"error": "File not found"}, status_code=404)
            
        content = blob.download_as_text(encoding="utf-8")
        return _json({"content": content})
    except Exception as e:
        return _json({"error": str(e)}, status_code=500)

@router.post('/api/files/content')
async def files_save_content(request: Request):
    
    try:
        payload = await request.json()
        blob_name = payload.get("blob_name")
        content = payload.get("content")
        
        if not blob_name:
            return _json({"error": "blob_name is required"}, status_code=400)
            
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        
        # Determine content type
        content_type = "text/plain; charset=utf-8"
        if blob_name.lower().endswith(".md"):
            content_type = "text/markdown; charset=utf-8"
            
        blob.upload_from_string(content, content_type=content_type)
        
        # Invalidate caches
        list_uploaded_files_cached.clear()
        load_memo_list_cached.clear()
        
        return _json({"status": "ok"})
    except Exception as e:
        return _json({"error": str(e)}, status_code=500)
