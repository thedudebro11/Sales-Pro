"""
Sales Pro Web UI — FastAPI backend with SSE streaming.
"""
import json
import queue
import threading
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

import config

app = FastAPI(title="Sales Pro")


@app.on_event("startup")
async def startup():
    import database
    database.init_db()

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


class ProspectCreate(BaseModel):
    business_name: str
    owner_name: str = ""
    city: str = ""
    state: str = ""
    industry: str = ""
    website_url: str = ""
    phone: str = ""
    email: str = ""
    stage: str = "researched"
    notes: str = ""


class ProspectUpdate(BaseModel):
    stage: str | None = None
    notes: str | None = None
    owner_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website_url: str | None = None


class InteractionCreate(BaseModel):
    type: str = "call"
    outcome: str = ""
    opener_used: str = ""
    objections: str = ""
    cta_used: str = ""
    cta_response: str = ""
    notes: str = ""
    duration_estimate: str = ""


class ClientCreate(BaseModel):
    prospect_id: int | None = None
    business_name: str
    owner_name: str = ""
    city: str = ""
    industry: str = ""
    phone: str = ""
    email: str = ""
    start_date: str = ""
    monthly_value: float = 0
    total_contract_value: float = 0
    notes: str = ""


class ClientUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    monthly_value: float | None = None
    total_contract_value: float | None = None
    owner_name: str | None = None
    phone: str | None = None
    email: str | None = None


class InvoiceCreate(BaseModel):
    client_id: int
    amount: float
    description: str = ""
    due_date: str = ""


class InvoiceUpdate(BaseModel):
    status: str | None = None
    paid_date: str | None = None
    amount: float | None = None


class DeliverableCreate(BaseModel):
    client_id: int
    title: str
    description: str = ""
    due_date: str = ""


class DeliverableUpdate(BaseModel):
    status: str | None = None
    completed_at: str | None = None


class ResearchRequest(BaseModel):
    business_name: str
    city: str = ""
    industry: str = ""
    website_url: str = ""
    gbp_notes: str = ""


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


# ── CRM / Dashboard endpoints ────────────────────────────────────────────────

@app.get("/api/dashboard")
async def api_dashboard():
    import database
    conn = database.get_db()
    try:
        followups_rows = conn.execute(
            "SELECT f.*, p.business_name FROM followups f "
            "LEFT JOIN prospects p ON f.prospect_id = p.id "
            "WHERE f.scheduled_for <= date('now') AND f.completed = 0 "
            "ORDER BY f.scheduled_for"
        ).fetchall()

        counts_rows = conn.execute(
            "SELECT stage, COUNT(*) as cnt FROM prospects GROUP BY stage"
        ).fetchall()

        revenue_owed = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status IN ('unpaid', 'overdue')"
        ).fetchone()[0]

        revenue_collected = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM invoices "
            "WHERE status = 'paid' AND strftime('%Y-%m', paid_date) = strftime('%Y-%m', 'now')"
        ).fetchone()[0]

        active_clients = conn.execute(
            "SELECT COUNT(*) FROM clients WHERE status = 'active'"
        ).fetchone()[0]

        pipeline_value = conn.execute(
            "SELECT COALESCE(SUM(total_contract_value), 0) FROM clients WHERE status = 'active'"
        ).fetchone()[0]

        recent_invoices_rows = conn.execute(
            "SELECT i.*, c.business_name as client_name FROM invoices i "
            "LEFT JOIN clients c ON i.client_id = c.id "
            "ORDER BY i.created_at DESC LIMIT 5"
        ).fetchall()

        pipeline_counts = {}
        for r in counts_rows:
            pipeline_counts[r["stage"]] = r["cnt"]

        return JSONResponse({
            "followups_today": [dict(r) for r in followups_rows],
            "pipeline_counts": pipeline_counts,
            "revenue_owed": revenue_owed,
            "revenue_collected": revenue_collected,
            "active_clients": active_clients,
            "pipeline_value": pipeline_value,
            "recent_invoices": [dict(r) for r in recent_invoices_rows],
        })
    finally:
        conn.close()


@app.get("/api/pipeline")
async def api_pipeline():
    import database
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT p.*, "
            "(SELECT created_at FROM interactions WHERE prospect_id = p.id ORDER BY created_at DESC LIMIT 1) as last_interaction "
            "FROM prospects p ORDER BY p.updated_at DESC"
        ).fetchall()
        return JSONResponse([dict(r) for r in rows])
    finally:
        conn.close()


@app.post("/api/prospects")
async def api_create_prospect(req: ProspectCreate):
    import database
    conn = database.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO prospects (business_name, owner_name, city, state, industry, "
            "website_url, phone, email, stage, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (req.business_name, req.owner_name, req.city, req.state, req.industry,
             req.website_url, req.phone, req.email, req.stage, req.notes)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM prospects WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


@app.patch("/api/prospects/{prospect_id}")
async def api_update_prospect(prospect_id: int, req: ProspectUpdate):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")

        fields = req.dict(exclude_none=True)
        if not fields:
            return JSONResponse(dict(row))

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        set_clause += ", updated_at = datetime('now')"
        conn.execute(
            f"UPDATE prospects SET {set_clause} WHERE id = ?",
            [*fields.values(), prospect_id]
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        return JSONResponse(dict(updated))
    finally:
        conn.close()


@app.get("/api/followups/today")
async def api_followups_today():
    import database
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT f.*, p.business_name FROM followups f "
            "LEFT JOIN prospects p ON f.prospect_id = p.id "
            "WHERE f.scheduled_for <= date('now') AND f.completed = 0 "
            "ORDER BY f.scheduled_for"
        ).fetchall()
        return JSONResponse([dict(r) for r in rows])
    finally:
        conn.close()


@app.patch("/api/followups/{followup_id}/complete")
async def api_complete_followup(followup_id: int):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM followups WHERE id = ?", (followup_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        conn.execute("UPDATE followups SET completed = 1 WHERE id = ?", (followup_id,))
        conn.commit()
        return JSONResponse({"ok": True})
    finally:
        conn.close()


# ── Session B: Interactions ───────────────────────────────────────────────────

@app.get("/api/prospects/{prospect_id}")
async def api_get_prospect(prospect_id: int):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")
        interactions = conn.execute(
            "SELECT * FROM interactions WHERE prospect_id = ? ORDER BY created_at DESC",
            (prospect_id,)
        ).fetchall()
        followups = conn.execute(
            "SELECT * FROM followups WHERE prospect_id = ? ORDER BY scheduled_for",
            (prospect_id,)
        ).fetchall()
        data = dict(row)
        data["interactions"] = [dict(i) for i in interactions]
        data["followups"] = [dict(f) for f in followups]
        return JSONResponse(data)
    finally:
        conn.close()


@app.post("/api/prospects/{prospect_id}/interactions")
async def api_add_interaction(prospect_id: int, req: InteractionCreate):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")
        cur = conn.execute(
            "INSERT INTO interactions (prospect_id, type, outcome, opener_used, objections, "
            "cta_used, cta_response, notes, duration_estimate) VALUES (?,?,?,?,?,?,?,?,?)",
            (prospect_id, req.type, req.outcome, req.opener_used, req.objections,
             req.cta_used, req.cta_response, req.notes, req.duration_estimate)
        )
        conn.execute(
            "UPDATE prospects SET updated_at=datetime('now') WHERE id=?", (prospect_id,)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


@app.patch("/api/interactions/{interaction_id}")
async def api_update_interaction(interaction_id: int, body: dict):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (interaction_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Interaction not found")
        fields = {k: v for k, v in body.items() if k in ("type", "outcome", "notes", "opener_used", "cta_used", "cta_response")}
        if fields:
            set_clause = ", ".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE interactions SET {set_clause} WHERE id=?", (*fields.values(), interaction_id))
            conn.commit()
        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (interaction_id,)).fetchone()
        return JSONResponse(dict(row))
    finally:
        conn.close()


@app.delete("/api/interactions/{interaction_id}")
async def api_delete_interaction(interaction_id: int):
    import database
    conn = database.get_db()
    try:
        conn.execute("DELETE FROM interactions WHERE id = ?", (interaction_id,))
        conn.commit()
        return JSONResponse({"ok": True})
    finally:
        conn.close()


@app.post("/api/prospects/{prospect_id}/followups")
async def api_add_followup(prospect_id: int, body: dict):
    import database
    conn = database.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO followups (prospect_id, type, message_draft, scheduled_for) VALUES (?,?,?,?)",
            (prospect_id, body.get("type","call"), body.get("message_draft",""), body.get("scheduled_for",""))
        )
        conn.commit()
        row = conn.execute("SELECT * FROM followups WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


# ── Session B: Clients ────────────────────────────────────────────────────────

@app.get("/api/clients")
async def api_clients():
    import database
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT c.*, "
            "COALESCE((SELECT SUM(amount) FROM invoices WHERE client_id=c.id AND status IN ('unpaid','overdue')),0) as owed, "
            "COALESCE((SELECT SUM(amount) FROM invoices WHERE client_id=c.id AND status='paid'),0) as paid_total, "
            "(SELECT COUNT(*) FROM deliverables WHERE client_id=c.id) as deliverable_count, "
            "(SELECT COUNT(*) FROM deliverables WHERE client_id=c.id AND status IN ('done','approved')) as deliverable_done "
            "FROM clients c ORDER BY c.created_at DESC"
        ).fetchall()
        return JSONResponse([dict(r) for r in rows])
    finally:
        conn.close()


@app.post("/api/clients")
async def api_create_client(req: ClientCreate):
    import database
    conn = database.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO clients (prospect_id, business_name, owner_name, city, industry, "
            "phone, email, start_date, monthly_value, total_contract_value, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (req.prospect_id, req.business_name, req.owner_name, req.city, req.industry,
             req.phone, req.email, req.start_date, req.monthly_value, req.total_contract_value, req.notes)
        )
        if req.prospect_id:
            conn.execute(
                "UPDATE prospects SET stage='won', updated_at=datetime('now') WHERE id=?",
                (req.prospect_id,)
            )
        conn.commit()
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


@app.get("/api/clients/{client_id}")
async def api_client_detail(client_id: int):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")
        invoices = conn.execute(
            "SELECT * FROM invoices WHERE client_id = ? ORDER BY created_at DESC", (client_id,)
        ).fetchall()
        deliverables = conn.execute(
            "SELECT * FROM deliverables WHERE client_id = ? ORDER BY created_at", (client_id,)
        ).fetchall()
        data = dict(row)
        data["invoices"] = [dict(i) for i in invoices]
        data["deliverables"] = [dict(d) for d in deliverables]
        return JSONResponse(data)
    finally:
        conn.close()


@app.patch("/api/clients/{client_id}")
async def api_update_client(client_id: int, req: ClientUpdate):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")
        fields = req.dict(exclude_none=True)
        if fields:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", [*fields.values(), client_id])
            conn.commit()
        updated = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        return JSONResponse(dict(updated))
    finally:
        conn.close()


# ── Session B: Invoices ───────────────────────────────────────────────────────

@app.post("/api/invoices")
async def api_create_invoice(req: InvoiceCreate):
    import database
    conn = database.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO invoices (client_id, amount, description, due_date) VALUES (?,?,?,?)",
            (req.client_id, req.amount, req.description, req.due_date)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


@app.patch("/api/invoices/{invoice_id}")
async def api_update_invoice(invoice_id: int, req: InvoiceUpdate):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        fields = req.dict(exclude_none=True)
        if "status" in fields and fields["status"] == "paid" and "paid_date" not in fields:
            from datetime import date
            fields["paid_date"] = date.today().isoformat()
        if fields:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE invoices SET {set_clause} WHERE id = ?", [*fields.values(), invoice_id])
            conn.commit()
        updated = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return JSONResponse(dict(updated))
    finally:
        conn.close()


# ── Session B: Deliverables ───────────────────────────────────────────────────

@app.post("/api/deliverables")
async def api_create_deliverable(req: DeliverableCreate):
    import database
    conn = database.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO deliverables (client_id, title, description, due_date) VALUES (?,?,?,?)",
            (req.client_id, req.title, req.description, req.due_date)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM deliverables WHERE id = ?", (cur.lastrowid,)).fetchone()
        return JSONResponse(dict(row), status_code=201)
    finally:
        conn.close()


@app.patch("/api/deliverables/{deliverable_id}")
async def api_update_deliverable(deliverable_id: int, req: DeliverableUpdate):
    import database
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM deliverables WHERE id = ?", (deliverable_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        fields = req.dict(exclude_none=True)
        if "status" in fields and fields["status"] in ("done", "approved") and "completed_at" not in fields:
            from datetime import date
            fields["completed_at"] = date.today().isoformat()
        if fields:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE deliverables SET {set_clause} WHERE id = ?", [*fields.values(), deliverable_id])
            conn.commit()
        updated = conn.execute("SELECT * FROM deliverables WHERE id = ?", (deliverable_id,)).fetchone()
        return JSONResponse(dict(updated))
    finally:
        conn.close()


# ── Session C: Call Logger (SSE) ─────────────────────────────────────────────

def _run_log_call(raw_audio: bytes, suffix: str, business_name: str,
                  industry: str, city: str, q: "queue.Queue[str | None]"):
    import tempfile
    try:
        from pipeline.call_logger import log_call

        def on_step(msg):
            q.put(_sse("step", msg))

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_audio)
            tmp_path = Path(tmp.name)

        result = log_call(tmp_path, business_name=business_name,
                          industry=industry, city=city, on_step=on_step)
        q.put(_sse("done", json.dumps(result)))
    except Exception as exc:
        q.put(_sse("error", str(exc)))
    finally:
        q.put(None)


@app.post("/api/log-call")
async def api_log_call(
    audio: UploadFile = File(...),
    business_name: str = Form(""),
    industry: str = Form(""),
    city: str = Form(""),
):
    raw = await audio.read()
    suffix = Path(audio.filename or "call.m4a").suffix or ".m4a"
    q: queue.Queue = queue.Queue()
    threading.Thread(
        target=_run_log_call,
        args=(raw, suffix, business_name, industry, city, q),
        daemon=True
    ).start()
    return StreamingResponse(_stream_queue(q), media_type="text/event-stream")


# ── Session C: Research (SSE) ─────────────────────────────────────────────────

def _run_research(req_data: dict, q: "queue.Queue[str | None]"):
    try:
        from pipeline.researcher import research_business

        def on_step(msg):
            q.put(_sse("step", msg))

        result = research_business(
            business_name=req_data.get("business_name", ""),
            city=req_data.get("city", ""),
            industry=req_data.get("industry", ""),
            website_url=req_data.get("website_url", ""),
            gbp_notes=req_data.get("gbp_notes", ""),
            on_step=on_step,
        )
        q.put(_sse("done", json.dumps(result)))
    except Exception as exc:
        q.put(_sse("error", str(exc)))
    finally:
        q.put(None)


@app.post("/api/research")
async def api_research(req: ResearchRequest):
    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_research, args=(req.dict(), q), daemon=True).start()
    return StreamingResponse(_stream_queue(q), media_type="text/event-stream")


# ── Session D: Audio Router (SSE) ────────────────────────────────────────────

def _run_audio_router(raw_audio: bytes, suffix: str, q: "queue.Queue[str | None]"):
    import tempfile
    try:
        from pipeline.audio_router import route_audio

        def on_step(msg):
            q.put(_sse("step", msg))

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_audio)
            tmp_path = Path(tmp.name)

        result = route_audio(tmp_path, on_step=on_step)
        q.put(_sse("done", json.dumps(result)))
    except Exception as exc:
        q.put(_sse("error", str(exc)))
    finally:
        q.put(None)


@app.post("/api/audio")
async def api_audio(audio: UploadFile = File(...)):
    raw = await audio.read()
    suffix = Path(audio.filename or "audio.m4a").suffix or ".m4a"
    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_audio_router, args=(raw, suffix, q), daemon=True).start()
    return StreamingResponse(_stream_queue(q), media_type="text/event-stream")


# ── Session E: Insights ───────────────────────────────────────────────────────

@app.get("/api/insights")
async def api_insights():
    import database
    conn = database.get_db()
    try:
        total_calls = conn.execute(
            "SELECT COUNT(*) FROM call_patterns WHERE created_at >= date('now','-7 days')"
        ).fetchone()[0]

        top_openers = conn.execute(
            "SELECT opener_type, outcome, COUNT(*) as cnt FROM call_patterns "
            "WHERE created_at >= date('now','-7 days') AND outcome IN ('interested','callback') "
            "AND opener_type != '' GROUP BY opener_type ORDER BY cnt DESC LIMIT 3"
        ).fetchall()

        industry_stats = conn.execute(
            "SELECT industry, COUNT(*) as total, "
            "SUM(CASE WHEN outcome IN ('interested','callback') THEN 1 ELSE 0 END) as positive "
            "FROM call_patterns WHERE created_at >= date('now','-7 days') AND industry != '' "
            "GROUP BY industry ORDER BY total DESC LIMIT 5"
        ).fetchall()

        top_cta = conn.execute(
            "SELECT cta_type, COUNT(*) as cnt FROM call_patterns "
            "WHERE created_at >= date('now','-7 days') AND outcome IN ('interested','callback') "
            "AND cta_type != '' GROUP BY cta_type ORDER BY cnt DESC LIMIT 1"
        ).fetchone()

        return JSONResponse({
            "total_calls_this_week": total_calls,
            "top_openers": [dict(r) for r in top_openers],
            "industry_stats": [dict(r) for r in industry_stats],
            "top_cta": dict(top_cta) if top_cta else None,
        })
    finally:
        conn.close()
