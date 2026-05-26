import os

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import FileResponse

from app.api_deps import _json, _file_response_bytes, get_current_user
from app.memo import create_zip_of_memos, delete_memo_txt, load_memo_list_cached, load_single_memo_content, save_memo_txt

router = APIRouter()

@router.get('/api/memos')
async def memos_list(request: Request, _: bool = Depends(get_current_user)):
    return _json({"memos": load_memo_list_cached()})

@router.get('/api/memos/zip')
async def memos_zip(request: Request, _: bool = Depends(get_current_user)):
    memos = load_memo_list_cached()
    zip_path = create_zip_of_memos(memos)
    if not zip_path or not os.path.exists(zip_path):
        return _json({"error": "다운로드할 메모가 없습니다."}, status_code=404)

    background = BackgroundTasks()
    background.add_task(os.remove, zip_path)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="jisong-cloud-memos.zip",
        background=background,
    )

@router.get('/api/memos/{file_name:str}')
async def memo_detail(request: Request, _: bool = Depends(get_current_user)):
    return _json({"memo": load_single_memo_content(request.path_params["file_name"])})

@router.get('/api/memos/{file_name:str}/download')
async def memo_download(request: Request, _: bool = Depends(get_current_user)):
    memo = load_single_memo_content(request.path_params["file_name"])
    filename = f"{memo.get('title') or 'memo'}.txt"
    return _file_response_bytes(
        (memo.get("content") or "").encode("utf-8"),
        filename,
        "text/plain; charset=utf-8",
    )

@router.post('/api/memos')
async def memo_save(request: Request, _: bool = Depends(get_current_user)):
    payload = await request.json()
    save_memo_txt(
        payload.get("title", "메모"),
        payload.get("content", ""),
        payload.get("file_name") or None,
    )
    return _json({"ok": True})

@router.post('/api/memos/delete')
async def memo_delete(request: Request, _: bool = Depends(get_current_user)):
    payload = await request.json()
    delete_memo_txt(payload.get("file_name", ""))
    return _json({"ok": True})
