from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

# We will inject the TaskManager instance from main.py
task_manager = None
notification_callback = None

from setup_manager import SetupManager
setup_mgr = SetupManager()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

import sys
import os
from pathlib import Path

# Fix for PyInstaller path
if hasattr(sys, '_MEIPASS'):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(os.path.abspath("."))

templates = Jinja2Templates(directory=str(base_path / "templates"))
logger = logging.getLogger(__name__)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    from config import CONFIG_FILE
    if not CONFIG_FILE.exists():
        return templates.TemplateResponse("wizard.html", {"request": request})
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/tasks")
async def get_tasks():
    if not task_manager:
        return []
    return await task_manager.get_tasks()

@app.post("/api/done/{task_id}")
async def mark_done(task_id: str):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
    
    # SSOT: Direct call
    await task_manager.mark_done(task_id)
    if notification_callback:
        # We might need to fetch the task to get the summary for the notification
        # For now, let's just notify generic success or skip summary
        await notification_callback(f"Task {task_id} marked as Done")
        
    return {"status": "success", "task": task_id}

@app.post("/api/reject/{task_id}")
async def reject_task(task_id: str):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
    
    # SSOT: Direct call
    await task_manager.reject_task(task_id)
    return {"status": "success", "task": task_id}

@app.post("/api/reopen/{task_id}")
async def reopen_task(task_id: str):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
    
    await task_manager.reopen_task(task_id)
    return {"status": "success", "task": task_id}

@app.get("/api/discussions/history")
async def get_discussion_history():
    from discussion_buffer import DiscussionBuffer
    db = DiscussionBuffer() # It loads from disk, so fresh instance is fine or can inject
    return db.get_history()

@app.get("/api/discussions/today")
async def get_today_discussion():
    from discussion_buffer import DiscussionBuffer
    db = DiscussionBuffer()
    return db.get_grouped_text() or "No discussions yet."

from pydantic import BaseModel
class CommentRequest(BaseModel):
    text: str
    sender: str = "User"

@app.get("/api/comments/{task_id}")
async def get_comments(task_id: str):
    if not task_manager: return []
    return await task_manager.get_comments(task_id)

@app.post("/api/comments/{task_id}")
async def add_comment(task_id: str, request: CommentRequest):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
    
    result = await task_manager.add_comment(task_id, request.text, request.sender)
    if result:
        return result
    return JSONResponse(status_code=500, content={"error": "Failed to add comment"})

@app.delete("/api/comments/{task_id}/{comment_id}")
async def delete_comment(task_id: str, comment_id: str):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
        
    success = await task_manager.delete_comment(task_id, comment_id)
    if success:
        return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "Comment not found or failed to delete"})


@app.post("/api/priority/{task_id}")
async def update_priority(task_id: str, request: dict):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
    
    priority = request.get("priority")
    if priority is None:
        return JSONResponse(status_code=400, content={"error": "Priority missing"})
        
    success = await task_manager.update_priority(task_id, priority)
    if success:
        return {"status": "success", "task": task_id, "priority": priority}
    return JSONResponse(status_code=500, content={"error": "Failed to update priority"})


@app.get("/api/audit")
async def get_audit_log():
    if not task_manager: return []
    return await task_manager.get_audit_log()

class CreateTaskRequest(BaseModel):
    summary: str
    priority: int
    sender: str
    link: str = None
    deadline: str = None

@app.post("/api/tasks/create")
async def create_task_manual(request: CreateTaskRequest):
    if not task_manager:
        return JSONResponse(status_code=500, content={"error": "TaskManager not initialized"})
        
    result = await task_manager.add_task(
        priority=request.priority,
        summary=request.summary,
        sender=request.sender,
        link=request.link,
        deadline=request.deadline
    )
    return result

# --- WIZARD SETUP ENDPOINTS ---
import json

class SetupInitRequest(BaseModel):
    api_id: int
    api_hash: str

@app.post("/api/setup/init")
async def setup_init(req: SetupInitRequest):
    try:
        await setup_mgr.connect(req.api_id, req.api_hash)
        return {"status": "connected"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class PhoneRequest(BaseModel):
    phone: str

@app.post("/api/setup/send_code")
async def setup_send_code(req: PhoneRequest):
    try:
        result = await setup_mgr.send_code(req.phone)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class CodeRequest(BaseModel):
    code: str

@app.post("/api/setup/verify_code")
async def setup_verify_code(req: CodeRequest):
    try:
        result = await setup_mgr.verify_code(req.code)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class PasswordRequest(BaseModel):
    password: str

@app.post("/api/setup/verify_password")
async def setup_verify_password(req: PasswordRequest):
    try:
        result = await setup_mgr.verify_password(req.password)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/setup/save")
async def setup_save_config(config: dict):
    from config import CONFIG_DIR, CONFIG_FILE
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return {"status": "success", "message": "Configuration saved."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/config")
async def get_current_config():
    from config import load_config
    return load_config()

@app.post("/api/config")
async def update_config(new_config: dict):
    from config import CONFIG_FILE, CONFIG_DIR
    try:
        # Load existing
        current = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                current = json.load(f)
        
        # Merge (only allow specific keys to be updated for safety)
        allowed_keys = [
            "ENABLE_AUTO_REPLY", 
            "WORKING_HOURS_START", 
            "WORKING_HOURS_END", 
            "ENABLE_LONG_TERM_MEMORY",
            "GROUP_TRIGGER_KEYWORDS",
            "CATCH_UP_SECONDS"
        ]
        
        for key in allowed_keys:
            if key in new_config:
                current[key] = new_config[key]
        
        # Save
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(current, f, indent=4)
            
        return {"status": "success", "message": "Settings updated. Restart may be required for some changes."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/setup/status")
async def get_setup_status():
    from config import CONFIG_FILE
    return {
        "is_configured": CONFIG_FILE.exists(),
        "config_path": str(CONFIG_FILE)
    }

