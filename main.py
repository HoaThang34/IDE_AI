# main.py
import os
import requests
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyAzEoB6TEKDv0yRyNtuQPapcLhRF86Axlk"
MODEL_NAME = "gemini-2.5-pro"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# THƯ MỤC GỐC (Thay đổi đường dẫn này nếu cần)
LOCAL_CODE_DIR = r"C:\Users\Admin\OneDrive\Code_C++"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class FileData(BaseModel):
    mimeType: str
    data: str

class ChatRequest(BaseModel):
    history: List[dict] = []
    message: str = ""
    files: List[FileData] = []

class FileSaveRequest(BaseModel):
    filename: str # Đường dẫn tương đối (VD: folder/bai1.cpp)
    content: str

# --- HELPER FUNCTION: QUÉT THƯ MỤC ĐỆ QUY ---
def scan_directory(path: str, relative_path: str = "") -> List[Dict[str, Any]]:
    items = []
    try:
        # Sắp xếp: Folder trước, File sau
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        
        for entry in entries:
            # Bỏ qua file/folder ẩn (.git, .vscode...)
            if entry.name.startswith('.'): 
                continue
                
            item_rel_path = os.path.join(relative_path, entry.name).replace("\\", "/")
            
            if entry.is_dir():
                items.append({
                    "name": entry.name,
                    "type": "folder",
                    "path": item_rel_path,
                    "children": scan_directory(entry.path, item_rel_path)
                })
            else:
                items.append({
                    "name": entry.name,
                    "type": "file",
                    "path": item_rel_path
                })
    except PermissionError:
        pass
    return items

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f: return f.read()
    except: return "File index.html not found"

@app.get("/explorer", response_class=HTMLResponse)
async def read_explorer():
    try:
        with open("explorer.html", "r", encoding="utf-8") as f: return f.read()
    except: return "File explorer.html not found"

# 1. API LIST FILES & FOLDERS (MỚI)
@app.get("/api/local/files")
async def list_files_tree():
    if not os.path.exists(LOCAL_CODE_DIR):
        return {"error": "Directory not found", "tree": []}
    
    # Trả về cấu trúc cây
    tree = scan_directory(LOCAL_CODE_DIR)
    return {"tree": tree, "root": LOCAL_CODE_DIR}

# 2. API READ FILE (Hỗ trợ đường dẫn con)
@app.get("/api/local/read")
async def read_file(filepath: str):
    try:
        # Security check: Đảm bảo file nằm trong LOCAL_CODE_DIR
        full_path = os.path.abspath(os.path.join(LOCAL_CODE_DIR, filepath))
        if not full_path.startswith(os.path.abspath(LOCAL_CODE_DIR)):
             return {"content": "// Access Denied"}

        if not os.path.exists(full_path):
            return {"content": "// File not found"}
            
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        return {"content": f"// Error: {str(e)}"}

# 3. API SAVE FILE (Hỗ trợ đường dẫn con)
@app.post("/api/local/save")
async def save_file(req: FileSaveRequest):
    try:
        full_path = os.path.abspath(os.path.join(LOCAL_CODE_DIR, req.filename))
        if not full_path.startswith(os.path.abspath(LOCAL_CODE_DIR)):
             return {"status": "error", "message": "Access Denied"}

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "success", "message": f"Saved {req.filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 4. API CHAT (GIỮ NGUYÊN)
@app.post("/api/chat")
async def chat_gen(req: ChatRequest):
    try:
        prompt_path = "prompt.txt"
        system_text = "Bạn là trợ lý lập trình."
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f: system_text = f.read()

        contents = []
        for turn in req.history:
            contents.append({"role": turn.get("role", "user"), "parts": turn.get("parts", [{"text": ""}])})

        curr_parts = []
        if req.message: curr_parts.append({"text": req.message})
        for f in req.files:
            curr_parts.append({"inline_data": {"mime_type": f.mimeType, "data": f.data}})
        
        if curr_parts: contents.append({"role": "user", "parts": curr_parts})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_text}]},
            "generationConfig": {"temperature": 0.7}
        }
        
        resp = requests.post(API_URL, headers={'Content-Type': 'application/json'}, json=payload)
        if resp.status_code != 200: return {"error": f"API Error: {resp.text}"}
        
        return {"result": resp.json()['candidates'][0]['content']['parts'][0]['text']}
    except Exception as e:
        return {"error": str(e)}

app.mount("/", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Server running at: http://localhost:80")
    uvicorn.run(app, host="0.0.0.0", port=80)