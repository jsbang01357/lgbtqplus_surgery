import logging
from contextlib import asynccontextmanager
import mimetypes

from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
from starlette.background import BackgroundTasks
from app.access_logger import log_access_request

from app.api_deps import _render_frontend_html, _request_client_host, FRONTEND_DIR, _cleanup_expired_sessions, _json
from app.request_utils import get_client_ip

from app.routers import auth, surgery

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app):
    _cleanup_expired_sessions()
    yield

app = FastAPI(title='Qplus Surgery API', lifespan=lifespan)

app.include_router(auth.router)
app.include_router(surgery.router)

@app.get("/api/health")
async def health(_request: Request):
    return _json({"ok": True, "service": "jisong-cloud-api"})

async def frontend(request: Request):
    path = request.path_params.get("path") or "index.html"
    target = (FRONTEND_DIR / path).resolve()
    if FRONTEND_DIR not in target.parents and target != FRONTEND_DIR:
        return Response("not found", status_code=404)
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        target = FRONTEND_DIR / "index.html"
    if target == (FRONTEND_DIR / "index.html").resolve():
        response = Response(_render_frontend_html(), media_type="text/html")
        if not request.cookies.get("jisong_access_logged"):
            client_ip = get_client_ip(request.headers, _request_client_host(request))
            headers_dict = dict(request.headers)
            tasks = BackgroundTasks()
            tasks.add_task(log_access_request, headers_dict, client_ip)
            response.background = tasks
            response.set_cookie("jisong_access_logged", "1", max_age=3600 * 24)
        return response
    media_type = mimetypes.guess_type(target.name)[0]
    return FileResponse(target, media_type=media_type)

@app.get("/")
async def frontend_root(request: Request):
    return await frontend(request)

@app.get("/{path:path}")
async def frontend_path(request: Request, path: str):
    return await frontend(request)
