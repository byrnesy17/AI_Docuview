import os, io, json, hashlib, tempfile, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

import gradio as gr
import pdfplumber
from pdf2image import convert_from_path
from docx import Document
from PIL import Image, ImageDraw

# Optional semantic model
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SBERT = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    SBERT = None
    np = None

# OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# ---------- Paths ----------
BASE = Path("search_index")
BASE.mkdir(exist_ok=True)
IMG_CACHE = BASE / "page_images"
IMG_CACHE.mkdir(exist_ok=True)
DB_PATH = BASE / "index.db"

# ---------- Helpers ----------
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf8")).hexdigest()

def ensure_db():
    import sqlite3
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT,
            path TEXT,
            meta JSON
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            page_id TEXT PRIMARY KEY,
            doc_id TEXT,
            page_num INTEGER,
            text TEXT,
            sentences JSON,
            words JSON,
            image_path TEXT
        );
    """)
    try:
        cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(page_id, text);")
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            page_id TEXT PRIMARY KEY,
            vector BLOB
        );
    """)
    con.commit()
    con.close()

ensure_db()

# ---------- Extraction ----------
def extract_pdf_pages(pdf_path: str) -> List[Dict[str,Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, p in enumerate(pdf.pages):
            text = p.extract_text() or ""
            if not text.strip() and OCR_AVAILABLE:
                # OCR fallback
                im = p.to_image(resolution=300).original
                text = pytesseract.image_to_string(im)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            words = []
            for w in p.extract_words():
                words.append({
                    "text": w.get("text",""),
                    "x0": float(w.get("x0",0)),
                    "x1": float(w.get("x1",0)),
                    "top": float(w.get("top",0)),
                    "bottom": float(w.get("bottom",0))
                })
            pages.append({"page_num": i+1, "text": text, "sentences": sentences, "words": words})
    return pages

def extract_docx_pages(docx_path: str, chars_per_chunk:int=2000) -> List[Dict[str,Any]]:
    doc = Document(docx_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    pages = []
    i = 0
    page_num = 1
    while i < len(text):
        chunk = text[i:i+chars_per_chunk]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk) if s.strip()]
        pages.append({"page_num": page_num, "text": chunk, "sentences": sentences, "words": []})
        i += chars_per_chunk
        page_num += 1
    return pages

def extract_zip_entries(zip_path: str) -> List[str]:
    import zipfile
    tmpdir = Path(tempfile.mkdtemp(prefix="zip_extract_"))
    outfiles = []
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.lower().endswith((".pdf", ".docx")):
                dest = tmpdir / Path(name).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                outfiles.append(str(dest))
    return outfiles

# ---------- Rendering ----------
def render_pdf_page_to_image(pdf_path: str, page_num: int) -> str:
    key = sha1(f"{pdf_path}:{page_num}")
    out = IMG_CACHE / f"{key}.png"
    if out.exists():
        return str(out)
    pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, fmt="png")
    if not pages:
        raise RuntimeError("pdf2image failed")
    im = pages[0].convert("RGB")
    im.save(out, "PNG")
    return str(out)

# ---------- Indexing ----------
def index_file(path: str, compute_embeddings: bool = False):
    import sqlite3
    path = str(path)
    fname = Path(path).name
    doc_id = sha1(path + str(os.path.getmtime(path)))
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO documents (doc_id, filename, path, meta) VALUES (?, ?, ?, ?)",
                (doc_id, fname, path, json.dumps({})))
    pages = []
    if path.lower().endswith(".pdf"):
        pages = extract_pdf_pages(path)
    elif path.lower().endswith(".docx"):
        pages = extract_docx_pages(path)
    elif path.lower().endswith(".zip"):
        files = extract_zip_entries(path)
        for f in files:
            index_file(f, compute_embeddings=compute_embeddings)
        con.commit()
        con.close()
        return doc_id

    for p in pages:
        page_id = sha1(doc_id + ":" + str(p["page_num"]))
        image_path = None
        if path.lower().endswith(".pdf"):
            try:
                image_path = render_pdf_page_to_image(path, p["page_num"])
            except Exception:
                image_path = None
        cur.execute("INSERT OR REPLACE INTO pages (page_id, doc_id, page_num, text, sentences, words, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (page_id, doc_id, p["page_num"], p["text"], json.dumps(p["sentences"]), json.dumps(p["words"]), image_path))
        try:
            cur.execute("INSERT INTO pages_fts (page_id, text) VALUES (?, ?)", (page_id, p["text"]))
        except Exception:
            pass
        if compute_embeddings and SBERT is not None and (p["text"] or "").strip():
            vec = SBERT.encode(p["text"], convert_to_numpy=True)
            cur.execute("INSERT OR REPLACE INTO embeddings (page_id, vector) VALUES (?, ?)", (page_id, vec.tobytes()))
    con.commit()
    con.close()
    return doc_id

def index_files_parallel(paths: List[str], compute_embeddings: bool=False):
    with ThreadPoolExecutor(max_workers=max(2, os.cpu_count()//2)) as ex:
        futures = [ex.submit(index_file, p, compute_embeddings) for p in paths]
        for f in futures:
            f.result()
    return True

# ---------- Search ----------
def fts_query(query: str, limit:int=50) -> List[Dict[str,Any]]:
    import sqlite3
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        cur.execute("SELECT p.page_id, p.doc_id, p.page_num, p.text, p.sentences, p.words, p.image_path FROM pages_fts JOIN pages p USING(page_id) WHERE pages_fts MATCH ? LIMIT ?;", (query, limit))
    except Exception:
        cur.execute("SELECT page_id, doc_id, page_num, text, sentences, words, image_path FROM pages WHERE text LIKE ? LIMIT ?;", (f"%{query}%", limit))
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "page_id": r["page_id"],
            "doc_id": r["doc_id"],
            "page_num": r["page_num"],
            "text": r["text"],
            "sentences": json.loads(r["sentences"] or "[]"),
            "words": json.loads(r["words"] or "[]"),
            "image_path": r["image_path"]
        })
    con.close()
    return out

def semantic_query(query: str, top_k:int=20) -> List[Dict[str,Any]]:
    if SBERT is None:
        raise RuntimeError("Semantic model not available.")
    qvec = SBERT.encode(query, convert_to_numpy=True)
    import sqlite3
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT page_id, vector FROM embeddings;")
    rows = cur.fetchall()
    scores = []
    for pid, vecbytes in rows:
        vec = np.frombuffer(vecbytes, dtype=np.float32)
        score = float(np.dot(qvec, vec) / ((np.linalg.norm(qvec)*np.linalg.norm(vec))+1e-9))
        scores.append((score, pid))
    scores.sort(reverse=True, key=lambda x: x[0])
    selected = [pid for _, pid in scores[:top_k]]
    out = []
    for pid in selected:
        cur.execute("SELECT page_id, doc_id, page_num, text, sentences, words, image_path FROM pages WHERE page_id=?;", (pid,))
        r = cur.fetchone()
        if r:
            out.append({
                "page_id": r[0],
                "doc_id": r[1],
                "page_num": r[2],
                "text": r[3],
                "sentences": json.loads(r[4] or "[]"),
                "words": json.loads(r[5] or "[]"),
                "image_path": r[6]
            })
    con.close()
    return out

# ---------- Sentence matching ----------
def find_best_sentence(sentences: List[str], q: str) -> str:
    ql = q.lower()
    for s in sentences:
        if ql in s.lower():
            return s
    # fallback fuzzy
    best, bestsc = "", 0.0
    import difflib
    for s in sentences:
        r = difflib.SequenceMatcher(None, s.lower(), ql).ratio()
        if r > bestsc:
            bestsc = r
            best = s
    return best or (sentences[0] if sentences else "")

def sentence_to_rects(words: List[Dict[str,Any]], sentence: str, image_path: str) -> List[Tuple[int,int,int,int]]:
    if not words or not sentence or not image_path:
        return []
    s_norm = re.sub(r'\s+', ' ', sentence).strip().lower()
    word_texts = [w.get("text","") for w in words]
    joined = " ".join(word_texts).lower()
    idx = joined.find(s_norm)
    matched_indices = []
    if idx != -1:
        s_tokens = s_norm.split()
        for i in range(len(word_texts)):
            if word_texts[i].lower().startswith(s_tokens[0]):
                ok = True
                for j, tok in enumerate(s_tokens):
                    if i+j >= len(word_texts) or word_texts[i+j].lower().strip('.,') != tok.strip('.,'):
                        ok = False
                        break
                if ok:
                    matched_indices = list(range(i, min(len(word_texts), i+len(s_tokens))))
                    break
    if not matched_indices:
        tokens = set(re.findall(r"\w+", s_norm))
        for i,w in enumerate(word_texts):
            if any(t in w.lower() for t in tokens):
                matched_indices.append(i)
    bboxes = []
    for i in matched_indices:
        w = words[i]
        bboxes.append((w["x0"], w["top"], w["x1"], w["bottom"]))
    if not bboxes:
        return []
    xs = [b[2] for b in bboxes] + [w.get("x1",0) for w in words]
    ys = [b[3] for b in bboxes] + [w.get("bottom",0) for w in words]
    pdf_w = max(xs) if xs else 1000
    pdf_h = max(ys) if ys else 1000
    img = Image.open(image_path)
    img_w, img_h = img.size
    sx = img_w / (pdf_w + 1e-9)
    sy = img_h / (pdf_h + 1e-9)
    rects = []
    for (x0, top, x1, bottom) in bboxes:
        rects.append((int(x0*sx), int(top*sy), int(x1*sx), int(bottom*sy)))
    # merge rects vertically if close
    merged = []
    bboxes = sorted(rects, key=lambda r: (r[1], r[0]))
    for r in bboxes:
        if not merged:
            merged.append(r)
        else:
            lx0, ly0, lx1, ly1 = merged[-1]
            x0,y0,x1,y1 = r
            if y0 <= ly1 + 8:
                merged[-1] = (min(lx0,x0), min(ly0,y0), max(lx1,x1), max(ly1,y1))
            else:
                merged.append(r)
    return merged

def create_overlay(image_path: str, rects: List[Tuple[int,int,int,int]]) -> str:
    if not rects:
        return image_path
    base = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (255,255,255,0))
    draw = ImageDraw.Draw(overlay)
    for (x0,y0,x1,y1) in rects:
        draw.rounded_rectangle([(x0,y0),(x1,y1)], radius=6, fill=(255,238,147,160))
    combined = Image.alpha_composite(base, overlay)
    out = Path(str(image_path)).with_suffix("")
    outpath = str(out) + "_hl.png"
    combined.save(outpath)
    return outpath

# ---------- Gradio UI ----------
CSS = """
body{ font-family: Inter,Roboto,sans-serif; background:#071223; color:#e6eef8; margin:0; }
h2{margin:0;}
.panel{background:rgba(255,255,255,0.02);border-radius:12px;padding:14px;margin-bottom:12px;}
.file-item{padding:6px 10px;margin-bottom:6px;border-radius:6px;background:rgba(255,255,255,0.05);}
.results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px;}
.card{background:white;color:#0b1220;border-radius:10px;padding:12px;box-shadow:0 8px 30px rgba(2,6,23,0.06);}
.view-btn{background:#6C8EF5;padding:6px 10px;color:white;border-radius:6px;border:none;cursor:pointer;}
.small-muted{color:#9aa7b8;font-size:13px;}
"""

with gr.Blocks(css=CSS, title="Legal Doc Search Pro") as demo:
    gr.Markdown("<h2>Legal Document Search Pro</h2><div class='small-muted'>Search across multiple documents and view highlighted matches inline</div>")
    file_input = gr.File(file_count="multiple", file_types=[".pdf",".docx",".zip"])
    files_preview = gr.HTML("<div class='small-muted'>No files selected</div>")
    index_btn = gr.Button("Index selected files")
    compute_emb_chk = gr.Checkbox(label="Compute semantic embeddings (optional)", value=False)
    query = gr.Textbox(placeholder="Enter search term...")
    mode_radio = gr.Radio(choices=["literal","semantic"], value="literal", label=None)
    search_btn = gr.Button("Search")
    search_status = gr.HTML("<div class='small-muted'>Ready</div>")
    results_html = gr.HTML("<div class='small-muted'>No results yet</div>")

    file_input.upload(lambda files: "<br>".join([f"<div class='file-item'>{Path(f).name}</div>" for f in files]) if files else "<div class='small-muted'>No files selected</div>", inputs=file_input, outputs=files_preview)

    index_btn.click(lambda files, emb: (index_files_parallel(files, compute_embeddings=emb), "<div class='small-muted'>Indexing complete</div>") if files else "<div class='small-muted'>No files selected</div>", inputs=[file_input, compute_emb_chk], outputs=search_status)

    def search_ui(q, mode):
        if not q.strip(): return "<div class='small-muted'>Enter a search term.</div>"
        try:
            pages = semantic_query(q) if mode=="semantic" else fts_query(q)
        except Exception as e:
            return f"<div class='small-muted'>Search failed: {e}</div>"
        if not pages: return "<div class='small-muted'>No matches found.</div>"
        grouped = {}
        for p in pages:
            doc = p.get("doc_id","unknown")[:8]
            grouped.setdefault(doc, []).append(p)
        cards = []
        for doc_id, doc_pages in grouped.items():
            cards.append(f"<div class='panel'><strong>Document: {doc_id} — {len(doc_pages)} match(es)</strong></div>")
            for p in doc_pages:
                sent = find_best_sentence(p.get("sentences", []), q)
                overlay_path = ""
                if p.get("image_path") and sent:
                    rects = sentence_to_rects(p.get("words", []), sent, p.get("image_path"))
                    overlay_path = create_overlay(p.get("image_path"), rects)
                cards.append(f"""
                    <div class='card'>
                        <strong>Page {p.get('page_num')}</strong>
                        <div class='small-muted' style='margin:8px 0'>{(sent[:400]).replace('<','&lt;')}</div>
                        <a href="file://{overlay_path}" target="_blank" class='view-btn'>View Page</a>
                    </div>
                """)
        return "<div class='results-grid'>" + "".join(cards) + "</div>"

    search_btn.click(search_ui, inputs=[query, mode_radio], outputs=results_html)

if __name__=="__main__":
    demo.launch()
