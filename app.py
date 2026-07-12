import json
import os
import uvicorn
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from fastapi.responses import PlainTextResponse, Response

from backend.orchestrator import run_query
from auth import router as auth_router, get_current_user
from agents.data_analysis import upload_file as da_upload, get_session_data as da_get_data
from agents.letter_generator import (
    get_document as lg_get_document,
    build_docx as lg_build_docx,
    send_email as lg_send_email,
    get_session_info as lg_get_session,
)
from agents.report_generator import (
    get_document as rg_get_document,
    build_docx as rg_build_docx,
    send_email as rg_send_email,
    get_session_info as rg_get_session,
)

app = FastAPI(title="SMARTAssist Hub", version="7.0")

# ── Session & Auth ──
_SECRET_KEY = os.getenv("SECRET_KEY", "smartassist-hub-change-this-in-production")

# Protect all routes except /login, /auth/*, /static/*
# NOTE: add AuthGate BEFORE SessionMiddleware so Starlette wraps them in correct order
# (middlewares run outermost-first; last registered = outermost)
class AuthGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public = path.startswith("/static") or path in ("/login", "/auth/google", "/auth/callback")
        if not public and not request.session.get("user"):
            return RedirectResponse("/login")
        return await call_next(request)

app.add_middleware(AuthGate)
app.add_middleware(SessionMiddleware, secret_key=_SECRET_KEY, session_cookie="smartassist_session", max_age=86400 * 7)
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

_jinja_env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

_sessions: dict[str, list[dict]] = {}
_session_meta: dict[str, dict] = {}
_feedback: list[dict] = []

AGENT_LABELS = {
    "data_analysis": {"icon": "\U0001f4ca", "name": "Analisis Data"},
    "letter_generator": {"icon": "✉️", "name": "Penjana Surat"},
    "report_generator": {"icon": "\U0001f4cb", "name": "Penjana Laporan"},
    "document_reviewer": {"icon": "\U0001f4dd", "name": "Semakan Dokumen"},
    "kpm_support": {"icon": "\U0001f6df", "name": "Sokongan KPM"},
    "fallback": {"icon": "\U0001f4ac", "name": "Pembantu Umum"},
}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int
    feedback: str  # 'up' or 'down'
    agent: str = ""


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", email: str = ""):
    if request.session.get("user"):
        return RedirectResponse("/")
    template = _jinja_env.get_template("login.html")
    html = template.render(error=error, email=email)
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    agents_list = [
        {"key": k, "icon": v["icon"], "name": v["name"]}
        for k, v in AGENT_LABELS.items()
        if k != "fallback"
    ]
    user = get_current_user(request)
    template = _jinja_env.get_template("index.html")
    html = template.render(agents_list=agents_list, user=user)
    return HTMLResponse(html)


class AgentChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    agent: str = ""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    history = _sessions.setdefault(req.session_id, [])
    history.append({"role": "user", "content": req.message})

    result = run_query(query=req.message, conversation_history=history, session_id=req.session_id)

    agent = result.get("active_agent", "fallback")
    output = result.get("agent_output", "Tiada respons.")

    history.append({"role": "assistant", "content": output, "agent": agent})

    if req.session_id not in _session_meta:
        _session_meta[req.session_id] = {
            "agent": agent,
            "title": req.message[:60],
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "message_count": 0,
        }
    meta = _session_meta[req.session_id]
    meta["updated"] = datetime.now().isoformat()
    meta["message_count"] = len(history)
    meta["agent"] = agent

    agent_info = AGENT_LABELS.get(agent, {"icon": "\U0001f4ac", "name": agent})

    structured = None
    if agent in ("data_analysis", "letter_generator", "report_generator", "document_reviewer"):
        try:
            structured = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            pass

    return JSONResponse({
        "response": output,
        "agent": agent,
        "agent_icon": agent_info["icon"],
        "agent_name": agent_info["name"],
        "structured": structured,
    })


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), session_id: str = Form("default")):
    contents = await file.read()
    result = da_upload(contents, file.filename, session_id)

    if result["ok"]:
        history = _sessions.setdefault(session_id, [])
        history.append({
            "role": "assistant",
            "content": f"Fail '{result['filename']}' berjaya dimuat naik. "
                       f"{result['rows']} baris x {result['columns']} lajur. "
                       f"Lajur: {', '.join(result['column_names'][:15])}"
                       f"{'...' if len(result['column_names']) > 15 else ''}",
            "agent": "data_analysis",
        })

    return JSONResponse(result)


@app.post("/api/review/upload")
async def review_upload(file: UploadFile = File(...), session_id: str = Form("default")):
    """Extract text from PDF or DOCX and store in document reviewer session."""
    import io as _io
    fname = file.filename or ""
    ext = _Path(fname).suffix.lower()
    allowed = {".pdf", ".docx", ".doc"}
    if ext not in allowed:
        return JSONResponse({"ok": False, "error": f"Format tidak disokong: {ext}. Sila gunakan PDF atau Word (.docx)."}, status_code=400)

    raw = await file.read()
    text = ""
    doc_type = "Dokumen"

    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(_io.BytesIO(raw)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(p for p in pages if p.strip())
            doc_type = "PDF"
        elif ext in (".docx", ".doc"):
            from docx import Document as _DocxDoc
            doc = _DocxDoc(_io.BytesIO(raw))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            doc_type = "Word (.docx)"
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Gagal membaca fail: {e}"}, status_code=500)

    if not text.strip():
        return JSONResponse({"ok": False, "error": "Fail kosong atau teks tidak dapat diekstrak."}, status_code=400)

    from agents.document_reviewer import set_uploaded_document
    set_uploaded_document(session_id, text, fname, doc_type)

    # Add to session history so context is preserved
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": f"[Fail dimuat naik: {fname}]"})

    return JSONResponse({
        "ok": True,
        "filename": fname,
        "doc_type": doc_type,
        "char_count": len(text),
        "preview": text[:300],
    })


@app.get("/api/data-status")
async def data_status(session_id: str = "default"):
    data = da_get_data(session_id)
    if data:
        return JSONResponse({
            "has_data": True,
            "filename": data["filename"],
            "shape": data["shape"],
            "columns": data["columns"],
        })
    return JSONResponse({"has_data": False})


@app.get("/api/document/download")
async def download_document(session_id: str = "default"):
    docx_bytes = lg_build_docx(session_id)
    if not docx_bytes:
        return JSONResponse({"error": "Tiada dokumen sedia untuk dimuat turun."}, status_code=404)
    info = lg_get_session(session_id)
    doc_type = info.get("doc_type", "dokumen") if info else "dokumen"
    filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/report/download")
async def download_report(session_id: str = "default"):
    docx_bytes = rg_build_docx(session_id)
    if not docx_bytes:
        return JSONResponse({"error": "Tiada laporan sedia untuk dimuat turun."}, status_code=404)
    filename = f"laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/report/save")
async def save_report(req: "SaveDocRequest"):
    session = rg_get_session(req.session_id)
    if session:
        session["document"] = req.content
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Sesi tidak ditemui."}, status_code=404)


@app.post("/api/report/send-email")
async def send_report_email(req: "EmailRequest"):
    result = rg_send_email(req.session_id, req.to_email, req.subject)
    return JSONResponse(result)


class SaveDocRequest(BaseModel):
    session_id: str = "default"
    content: str


@app.post("/api/document/save")
async def save_document(req: SaveDocRequest):
    from agents.letter_generator import get_session_info
    session = get_session_info(req.session_id)
    if session:
        session["document"] = req.content
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Sesi tidak ditemui."}, status_code=404)


class EmailRequest(BaseModel):
    session_id: str = "default"
    to_email: str
    subject: str


@app.post("/api/document/send-email")
async def send_document_email(req: EmailRequest):
    result = lg_send_email(req.session_id, req.to_email, req.subject)
    return JSONResponse(result)


class ExportRequest(BaseModel):
    session_id: str = "default"
    format: str = "pptx"
    data: dict
    chart_image: str | None = None


@app.post("/api/analysis/export")
async def export_analysis(req: ExportRequest):
    from agents.data_analysis_export import build_pptx, build_pdf
    try:
        if req.format == "pptx":
            content = build_pptx(req.data, chart_image_b64=req.chart_image)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": 'attachment; filename="analisis_data.pptx"'},
            )
        elif req.format == "pdf":
            content = build_pdf(req.data, chart_image_b64=req.chart_image)
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": 'attachment; filename="analisis_data.pdf"'},
            )
        else:
            return JSONResponse({"error": "Format tidak disokong."}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"Gagal menjana fail: {e}"}, status_code=500)


from backend.letterhead_store import (
    list_letterheads,
    get_active_by_type,
    add_letterhead,
    set_active as lh_set_active,
    delete_letterhead,
    update_name as lh_update_name,
)
from fastapi.responses import FileResponse as _FileResponse
from pathlib import Path as _Path


@app.get("/api/letterhead/list")
async def letterhead_list():
    data = list_letterheads()
    active_lh = get_active_by_type("letterhead")
    active_logo = get_active_by_type("logo")
    return JSONResponse({
        "letterheads": data,
        "active_letterhead_id": active_lh["id"] if active_lh else None,
        "active_logo_id": active_logo["id"] if active_logo else None,
    })


@app.get("/api/letterhead/active")
async def letterhead_active(lh_type: str = "letterhead"):
    lh = get_active_by_type(lh_type)
    return JSONResponse({"active": lh})


@app.post("/api/letterhead/upload")
async def letterhead_upload(
    file: UploadFile = File(...),
    label: str = Form(""),
    lh_type: str = Form("letterhead"),
):
    ext = _Path(file.filename).suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    if ext not in allowed:
        return JSONResponse({"ok": False, "error": f"Format tidak disokong: {ext}"}, status_code=400)
    data = await file.read()
    try:
        entry = add_letterhead(data, file.filename, label, lh_type)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    return JSONResponse({"ok": True, "letterhead": entry})


class LhSelectRequest(BaseModel):
    id: str
    lh_type: str = "letterhead"


@app.post("/api/letterhead/select")
async def letterhead_select(req: LhSelectRequest):
    ok = lh_set_active(req.id, req.lh_type)
    return JSONResponse({"ok": ok})


@app.post("/api/letterhead/rename")
async def letterhead_rename(req: dict):
    ok = lh_update_name(req.get("id", ""), req.get("name", ""))
    return JSONResponse({"ok": ok})


@app.delete("/api/letterhead/{lh_id}")
async def letterhead_delete(lh_id: str):
    ok = delete_letterhead(lh_id)
    return JSONResponse({"ok": ok})


@app.get("/api/letterhead/image/{filename}")
async def letterhead_image(filename: str):
    p = _Path("static/letterheads") / filename
    if not p.exists():
        return JSONResponse({"error": "Fail tidak ditemui."}, status_code=404)
    return _FileResponse(str(p))


@app.post("/api/clear")
async def clear(req: ChatRequest):
    _sessions.pop(req.session_id, None)
    from agents.data_analysis import clear_session_data
    from agents.letter_generator import clear_session as lg_clear
    from agents.report_generator import clear_session as rg_clear
    from agents.kpm_support import clear_session as kpm_clear
    from agents.document_reviewer import clear_session as dr_clear
    clear_session_data(req.session_id)
    lg_clear(req.session_id)
    rg_clear(req.session_id)
    kpm_clear(req.session_id)
    dr_clear(req.session_id)
    return JSONResponse({"status": "cleared"})


@app.get("/api/agents")
async def list_agents():
    return JSONResponse(AGENT_LABELS)


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    _feedback.append({
        "session_id": req.session_id,
        "message_index": req.message_index,
        "feedback": req.feedback,
        "agent": req.agent,
        "timestamp": datetime.now().isoformat(),
    })
    return JSONResponse({"ok": True})


@app.get("/api/stats")
async def get_stats():
    agent_counts: dict[str, int] = {}
    agent_messages: dict[str, int] = {}
    total_messages = 0
    for meta in _session_meta.values():
        agent = meta.get("agent", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
        mc = meta.get("message_count", 0)
        agent_messages[agent] = agent_messages.get(agent, 0) + mc
        total_messages += mc

    fb_by_agent: dict[str, dict] = {}
    for f in _feedback:
        a = f.get("agent", "unknown")
        if a not in fb_by_agent:
            fb_by_agent[a] = {"up": 0, "down": 0}
        fb_by_agent[a][f["feedback"]] = fb_by_agent[a].get(f["feedback"], 0) + 1

    recent = sorted(_session_meta.items(), key=lambda x: x[1].get("updated", ""), reverse=True)[:10]
    return JSONResponse({
        "total_sessions": len(_session_meta),
        "total_messages": total_messages,
        "agent_counts": agent_counts,
        "agent_messages": agent_messages,
        "feedback_total": {"up": sum(f["feedback"] == "up" for f in _feedback), "down": sum(f["feedback"] == "down" for f in _feedback)},
        "feedback_by_agent": fb_by_agent,
        "recent_sessions": [{"session_id": sid, **meta} for sid, meta in recent],
        "agent_labels": {k: v["name"] for k, v in AGENT_LABELS.items()},
    })


@app.get("/api/sessions")
async def list_sessions(agent: str = ""):
    sessions = []
    for sid, meta in _session_meta.items():
        if agent and meta.get("agent") != agent:
            continue
        sessions.append({"session_id": sid, **meta})
    sessions.sort(key=lambda s: s.get("updated", ""), reverse=True)
    return JSONResponse(sessions)


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    history = _sessions.get(session_id, [])
    messages = []
    for msg in history:
        agent = msg.get("agent", "")
        agent_info = AGENT_LABELS.get(agent, {"icon": "", "name": ""})
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "agent": agent,
            "agent_icon": agent_info.get("icon", ""),
            "agent_name": agent_info.get("name", ""),
        })
    return JSONResponse(messages)


@app.post("/api/agent-chat")
async def agent_chat(req: AgentChatRequest):
    """Direct chat with a specific agent, bypassing intent classification."""
    is_intro = req.message == "__INTRO__"
    history = _sessions.setdefault(req.session_id, [])
    if not is_intro:
        history.append({"role": "user", "content": req.message})

    agent = req.agent
    agent_info = AGENT_LABELS.get(agent, {"icon": "\U0001f4ac", "name": agent})

    try:
        from agents import data_analysis, letter_generator, kpm_support, report_generator, document_reviewer
        import inspect
        agent_map = {
            "data_analysis": data_analysis,
            "letter_generator": letter_generator,
            "kpm_support": kpm_support,
            "report_generator": report_generator,
            "document_reviewer": document_reviewer,
        }
        module = agent_map.get(agent)
        if module and hasattr(module, "handle"):
            sig = inspect.signature(module.handle)
            kwargs = {"query": req.message, "history": history}
            if "session_id" in sig.parameters:
                kwargs["session_id"] = req.session_id
            output = module.handle(**kwargs)

            # JSON retry: if agent expects JSON but output fails to parse, try once more
            JSON_AGENTS = {"data_analysis", "letter_generator", "report_generator", "document_reviewer"}
            if agent in JSON_AGENTS and not is_intro:
                try:
                    json.loads(output)
                except (json.JSONDecodeError, ValueError):
                    retry_kwargs = {**kwargs, "query": req.message + "\n\n[SISTEM: Balas HANYA dalam format JSON yang sah. Tiada teks lain di luar JSON.]"}
                    try:
                        output = module.handle(**retry_kwargs)
                    except Exception:
                        pass
        else:
            output = f"Agen '{agent}' tidak ditemui."
    except Exception as e:
        output = f"Ralat: {e}"

    if not is_intro:
        history.append({"role": "assistant", "content": output, "agent": agent})
        if req.session_id not in _session_meta:
            _session_meta[req.session_id] = {
                "agent": agent,
                "title": req.message[:60],
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
                "message_count": 0,
            }
        meta = _session_meta[req.session_id]
        meta["updated"] = datetime.now().isoformat()
        meta["message_count"] = len(history)

    structured = None
    if agent in ("data_analysis", "letter_generator", "report_generator", "document_reviewer"):
        try:
            structured = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            pass

    return JSONResponse({
        "response": output,
        "agent": agent,
        "agent_icon": agent_info["icon"],
        "agent_name": agent_info["name"],
        "structured": structured,
    })


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8112, reload=True)
