import os, re, json, hashlib, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

import gradio as gr
import pdfplumber
from pdf2image import convert_from_path
from docx import Document
from PIL import Image, ImageDraw
import numpy as np

# Semantic search
from sentence_transformers import SentenceTransformer
SBERT = SentenceTransformer("all-MiniLM-L6-v2")

# OCR
import pytesseract

# ---------- Paths ----------
BASE = Path("search_index")
BASE.mkdir(exist_ok=True)
IMG_CACHE = BASE / "page_images"
IMG_CACHE.mkdir(exist_ok=True)
DB_PATH = BASE / "index.json"  # simplified JSON storage for demo

# ---------- Helpers ----------
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf8")).hexdigest()

def load_db():
    if DB_PATH.exists():
        return json.load(open(DB_PATH, "r", encoding="utf8"))
    return {"documents": {}, "pages": {}, "embeddings": {}}

def save_db(db):
    json.dump(db, open(DB_PATH, "w", encoding="utf8"))

# ---------- Extraction ----------
def extract_pdf_pages(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, p in enumerate(pdf.pages):
            text = p.extract_text() or ""
            if not text.strip():
                im = p.to_image(resolution=300).original
                text = pytesseract.image_to_string(im)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            pages.append({"page_num": i + 1, "text": text, "sentences": sentences})
    return pages

def extract_docx_pages(docx_path: str, chars_per_chunk:int=2000) -> List[Dict[str,Any]]:
    doc = Document(docx_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    pages = []
    i, page_num = 0, 1
    while i < len(text):
        chunk = text[i:i+chars_per_chunk]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk) if s.strip()]
        pages.append({"page_num": page_num, "text": chunk, "sentences": sentences})
        i += chars_per_chunk
        page_num += 1
    return pages

def render_pdf_page_to_image(pdf_path: str, page_num: int) -> str:
    key = sha1(f"{pdf_path}:{page_num}")
    out = IMG_CACHE / f"{key}.png"
    if out.exists():
        return str(out)
    pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, fmt="png")
    if not pages: raise RuntimeError("pdf2image failed")
    pages[0].save(out, "PNG")
    return str(out)

# ---------- Indexing ----------
def index_file(path: str):
    db = load_db()
    path = str(path)
    fname = Path(path).name
    doc_id = sha1(path + str(os.path.getmtime(path)))
    db["documents"][doc_id] = {"filename": fname, "path": path}
    pages = []
    if path.lower().endswith(".pdf"):
        pages = extract_pdf_pages(path)
    elif path.lower().endswith(".docx"):
        pages = extract_docx_pages(path)
    else:
        return doc_id
    for p in pages:
        page_id = sha1(doc_id + ":" + str(p["page_num"]))
        image_path = None
        if path.lower().endswith(".pdf"):
            try:
                image_path = render_pdf_page_to_image(path, p["page_num"])
            except:
                image_path = None
        db["pages"][page_id] = {"doc_id": doc_id, "page_num": p["page_num"], "text": p["text"], "sentences": p["sentences"], "image_path": image_path}
        if p["text"].strip():
            vec = SBERT.encode(p["text"], convert_to_numpy=True).tolist()
            db["embeddings"][page_id] = vec
    save_db(db)
    return doc_id

def index_files_parallel(paths: List[str]):
    with ThreadPoolExecutor(max_workers=max(2, os.cpu_count()//2)) as ex:
        futures = [ex.submit(index_file, p) for p in paths]
        for f in futures: f.result()
    return True

# ---------- Search ----------
def semantic_query(query: str, top_k:int=20):
    db = load_db()
    qvec = SBERT.encode(query, convert_to_numpy=True)
    scores = []
    for pid, vec in db["embeddings"].items():
        vec_np = np.array(vec)
        score = float(np.dot(qvec, vec_np) / (np.linalg.norm(qvec)*np.linalg.norm(vec_np)+1e-9))
        scores.append((score, pid))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [db["pages"][pid] for _, pid in scores[:top_k]]

def literal_query(query: str):
    db = load_db()
    results = []
    ql = query.lower()
    for pid, p in db["pages"].items():
        if ql in p["text"].lower():
            results.append(p)
    return results[:50]

def find_best_sentence(sentences: List[str], q: str) -> str:
    ql = q.lower()
    for s in sentences:
        if ql in s.lower():
            return s
    return sentences[0] if sentences else ""

# ---------- Highlight Overlay ----------
def create_overlay(image_path: str) -> str:
    # Simplified: return image path (could add rectangle highlights if OCR word positions are stored)
    return image_path

# ---------- Gradio UI ----------
CSS = """
body{font-family:Inter,Roboto,sans-serif;background:#0c0f1c;color:#e6eef8;margin:0;}
h2{margin:0;}
.panel{background:rgba(255,255,255,0.03);border-radius:12px;padding:14px;margin-bottom:12px;}
.card{background:#1b1f33;color:#e6eef8;border-radius:10px;padding:12px;margin:6px 0;}
.view-btn{background:#6C8EF5;padding:6px 10px;color:white;border-radius:6px;border:none;cursor:pointer;}
.small-muted{color:#9aa7b8;font-size:13px;}
"""

def search_ui(q, mode):
    if not q.strip(): return "<div class='small-muted'>Enter a search term.</div>"
    try:
        pages = semantic_query(q) if mode=="semantic" else literal_query(q)
    except Exception as e:
        return f"<div class='small-muted'>Search failed: {e}</div>"
    if not pages: return "<div class='small-muted'>No matches found.</div>"
    cards = []
    for p in pages:
        sent = find_best_sentence(p.get("sentences", []), q)
        overlay_path = p.get("image_path")
        cards.append(f"""
        <div class='card'>
            <strong>{p.get('doc_id')[:8]} Page {p.get('page_num')}</strong>
            <div class='small-muted' style='margin:8px 0'>{sent[:300].replace('<','&lt;')}</div>
            {f'<a href="file://{overlay_path}" target="_blank" class="view-btn">View Page</a>' if overlay_path else ''}
        </div>
        """)
    return "<div class='panel'>" + "".join(cards) + "</div>"

with gr.Blocks(css=CSS, title="Legal Doc Search Pro") as demo:
    gr.Markdown("<h2>Legal Document Search Pro</h2><div class='small-muted'>Upload, index, and search across multiple documents with semantic understanding</div>")
    file_input = gr.File(file_count="multiple", file_types=[".pdf",".docx"])
    index_btn = gr.Button("Index Selected Files")
    query = gr.Textbox(placeholder="Enter search term...")
    mode_radio = gr.Radio(choices=["literal","semantic"], value="literal", label="Search Mode")
    search_btn = gr.Button("Search")
    results_html = gr.HTML("<div class='small-muted'>No results yet</div>")

    index_btn.click(index_files_parallel, inputs=[file_input], outputs=results_html)
    search_btn.click(search_ui, inputs=[query, mode_radio], outputs=results_html)

if __name__=="__main__":
    demo.launch()
