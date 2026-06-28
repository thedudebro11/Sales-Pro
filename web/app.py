"""
Sales Pro Web UI — FastAPI backend with SSE streaming.
"""
import json
import queue
import threading
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

import config

app = FastAPI(title="Sales Pro")

STATIC_DIR = Path(__file__).parent / "static"


# ── Request models ──────────────────────────────────────────────────────────

class AddRequest(BaseModel):
    url: str

class BatchRequest(BaseModel):
    urls: list[str]

class ScriptRequest(BaseModel):
    product: str
    audience: str
    platform: str = "Instagram Reels / TikTok"
    tone: str = "Conversational and confident"
    goal: str = "Book a call / DM for more info"

class RealisticScriptWebRequest(BaseModel):
    product: str
    audience: str
    platform: str = "Cold call and cold email"
    tone: str = "Helpful local operator, direct, realistic, consultative, not hypey"
    goal: str = "Book a free 15-minute Website + Google Business Profile audit"
    city: str = ""
    industry: str = ""
    target_business: str = ""
    observed_issues: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────

def _sse(stage: str, message: str) -> str:
    return f"data: {json.dumps({'stage': stage, 'message': message})}\n\n"


def _run_pipeline(url: str, q: "queue.Queue[str | None]"):
    """Run the full pipeline in a background thread, pushing SSE events to q."""
    from pipeline.downloader import download_instagram_video, extract_audio
    from pipeline.transcriber import transcribe
    from pipeline.analyzer import analyze
    from pipeline.vault_writer import write_to_vault, _find_existing_note_by_url

    try:
        # Duplicate check before touching network or disk
        existing = _find_existing_note_by_url(url)
        if existing:
            q.put(_sse("skipped", f"Already in vault: {existing.name}"))
            return

        q.put(_sse("starting", f"Processing: {url}"))
        with tempfile.TemporaryDirectory(prefix="sales_pro_") as tmpdir:
            tmp = Path(tmpdir)
            q.put(_sse("downloading", "Downloading video…"))
            video_path = download_instagram_video(url, output_dir=tmp)
            q.put(_sse("extracting", "Extracting audio…"))
            audio_path = extract_audio(video_path)
            q.put(_sse("transcribing", "Transcribing with Whisper (may take a minute)…"))
            transcript = transcribe(audio_path)
            q.put(_sse("analyzing", "Analyzing sales intelligence with Claude…"))
            data = analyze(transcript, url)
            q.put(_sse("writing", "Writing to Obsidian vault…"))
            note_path = write_to_vault(data)
        q.put(_sse("done", json.dumps({
            "title": data.get("title", ""),
            "tactics": len(data.get("tactics", [])),
            "hooks": len(data.get("hooks", [])),
            "note": str(note_path),
        })))
    except Exception as exc:
        q.put(_sse("error", str(exc)))
    finally:
        q.put(None)  # sentinel


async def _stream_queue(q: "queue.Queue[str | None]"):
    """Async generator that drains a thread-filled queue into SSE events."""
    import asyncio
    while True:
        try:
            item = q.get(timeout=0.05)
            if item is None:
                break
            yield item
        except queue.Empty:
            await asyncio.sleep(0.05)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/api/add")
async def api_add(req: AddRequest):
    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_pipeline, args=(req.url, q), daemon=True).start()
    return StreamingResponse(_stream_queue(q), media_type="text/event-stream")


@app.post("/api/batch")
async def api_batch(req: BatchRequest):
    async def stream():
        for i, url in enumerate(req.urls, 1):
            yield _sse("progress", f"[{i}/{len(req.urls)}] {url}")
            q: queue.Queue = queue.Queue()
            threading.Thread(target=_run_pipeline, args=(url, q), daemon=True).start()
            async for chunk in _stream_queue(q):
                yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/script")
async def api_script(req: ScriptRequest):
    import asyncio
    from agent.sales_agent import generate_script
    loop = asyncio.get_event_loop()
    script = await loop.run_in_executor(
        None,
        lambda: generate_script(req.product, req.audience, req.platform, req.tone, req.goal),
    )
    return JSONResponse({"script": script})


def _run_realistic_pipeline(req_data: dict, q: "queue.Queue[str | None]"):
    from agent.realistic_sales_agent import RealisticScriptRequest, generate_realistic_script

    def on_step(n: int, msg: str):
        q.put(_sse("step", json.dumps({"n": n, "msg": msg})))

    try:
        req = RealisticScriptRequest(**req_data)
        final = generate_realistic_script(req, on_step=on_step)
        q.put(_sse("done", final))
    except Exception as exc:
        q.put(_sse("error", str(exc)))
    finally:
        q.put(None)


@app.post("/api/realistic-script")
async def api_realistic_script(req: RealisticScriptWebRequest):
    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_realistic_pipeline, args=(req.dict(), q), daemon=True).start()
    return StreamingResponse(_stream_queue(q), media_type="text/event-stream")


@app.post("/api/upload-issues")
async def api_upload_issues(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return JSONResponse({"text": text})


@app.get("/api/brain")
async def api_brain():
    config.ensure_vault()
    stats = {name: len(list(path.glob("*.md"))) for name, path in config.VAULT_DIRS.items()}
    return JSONResponse(stats)
