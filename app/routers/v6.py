import logging
logger = logging.getLogger(__name__)
from fastapi import APIRouter, Request
from fastapi import Depends
import json
import secrets

from app.api_deps import _json, get_current_user
from app.gcs_helper import get_bucket
from app.v6_bridge import ParserBridgeError, parser_bridge_available, run_v6_parse

router = APIRouter()

@router.get('/api/v6/health')
async def v6_health(_request: Request):
    available, reason = parser_bridge_available()
    return _json(
        {
            "ok": True,
            "parser_bridge_available": available,
            "reason": reason,
        }
    )

@router.post('/api/v6/parse')
async def v6_parse(request: Request, _: bool = Depends(get_current_user)):

    payload = await request.json()
    raw_text = str(payload.get("raw_text") or payload.get("text") or "").strip()
    patient_id = str(payload.get("patient_id") or "").strip() or "patient_001"
    source = str(payload.get("source") or "emr").strip() or "emr"
    source_path = str(payload.get("source_path") or "").strip()

    if not raw_text:
        return _json({"error": "raw_text를 입력하세요."}, status_code=400)

    try:
        result = run_v6_parse(
            patient_id=patient_id,
            raw_text=raw_text,
            source=source,
            source_path=source_path,
        )
    except ParserBridgeError as exc:
        return _json({"error": str(exc)}, status_code=503)
    except Exception as exc:
        logger.exception("v6 parse failed")
        return _json({"error": str(exc)}, status_code=500)

    return _json(result)

@router.post('/api/v6/publish')
async def v6_publish_sync(request: Request, _: bool = Depends(get_current_user)):

    payload = await request.json()
    documents = payload.get("documents", [])
    manifest = payload.get("manifest", [])

    if not documents:
        return _json({"error": "동기화할 문서가 없습니다."}, status_code=400)

    bucket = get_bucket()
    synced_files = []

    for doc in documents:
        rel_path = doc.get("relativePath")
        content = doc.get("content", "")
        if not rel_path:
            continue

        blob_name = f"v6_sync/{rel_path}"
        blob = bucket.blob(blob_name)

        content_type = "text/plain; charset=utf-8"
        if rel_path.endswith(".csv"):
            content_type = "text/csv; charset=utf-8"
        elif rel_path.endswith(".md"):
            content_type = "text/markdown; charset=utf-8"

        blob.upload_from_string(content.encode("utf-8"), content_type=content_type)
        synced_files.append(blob_name)

    # Save manifest
    if manifest and documents:
        patient_id = documents[0].get("metadata", {}).get("patientId", "unknown")
        manifest_blob_name = (
            f"v6_sync/workspace/{patient_id}/_manifest_{secrets.token_hex(4)}.json"
        )
        manifest_blob = bucket.blob(manifest_blob_name)
        manifest_blob.upload_from_string(
            json.dumps(manifest).encode("utf-8"), content_type="application/json"
        )
        synced_files.append(manifest_blob_name)

    return _json({"ok": True, "synced_count": len(synced_files)})
