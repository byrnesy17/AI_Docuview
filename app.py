import os, re, hashlib
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

import gradio as gr
import pdfplumber
from docx import Document
from pdf2image import convert_from_path
import pytesseract
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------
# Initialization
# ---------------------------
MODEL = SentenceTransformer("all-MiniLM-L6-v2")
IMG_CACHE = Path("page_images")
IMG_CACHE.mkdir(exist_ok=True)

# ---------------------------
# Helpers
# ---------------------------
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf8")).hexdigest()

def save_pdf_page_image(pdf_path:str, page_num:int) -> str:
    key = sha1(f"{pdf_path}:{page_num}")+".png"
    path = IMG_CACHE / key
    if path.exists(): return str(path)
    pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
    pages[0].save(path, "PNG")
    return str(path)

def highlight_text(text:str, keywords:List[str]) -> str:
    for kw in sorted(keywords,key=len,reverse=True):
        text = re.sub(rf"(?i)\b({re.escape(kw)})\b", r"<mark>\1</mark>", text)
    return text

# ---------------------------
# Document Extraction
# ---------------------------
def extract_pdf_pages(pdf_path: str) -> List[Dict]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, p in enumerate(pdf.pages):
            text = p.extract_text() or ""
            if not text.strip():
                img = p.to_image(resolution=300).original
                text = pytesseract.image_to_string(img)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            img_path = save_pdf_page_image(pdf_path, i+1)
            pages.append({"page_num":i+1,"text":text,"sentences":sentences,"image":img_path})
    return pages

def extract_docx_pages(docx_path: str, chunk_size:int=2000) -> List[Dict]:
    doc = Document(docx_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    pages, i, page_num = [], 0, 1
    while i < len(text):
        chunk = text[i:i+chunk_size]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk) if s.strip()]
        pages.append({"page_num":page_num,"text":chunk,"sentences":sentences,"image":None})
        i += chunk_size
        page_num += 1
    return pages

def extract_txt(file_path:str) -> List[Dict]:
    text = Path(file_path).read_text(encoding="utf8")
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    return [{"page_num":1,"text":text,"sentences":sentences,"image":None}]

def load_documents(file_paths:List[str]) -> Dict[str,List[Dict]]:
    docs = {}
    for path in file_paths:
        path = str(path)
        if path.lower().endswith(".pdf"):
            docs[path] = extract_pdf_pages(path)
        elif path.lower().endswith(".docx"):
            docs[path] = extract_docx_pages(path)
        elif path.lower().endswith(".txt"):
            docs[path] = extract_txt(path)
    return docs

# ---------------------------
# Aligned Related Search Across Docs
# ---------------------------
def aligned_related_search(query:str, docs:Dict[str,List[Dict]], top_k:int=10, selected_docs:List[str]=None) -> Dict[str,List[Dict]]:
    all_sentences = []
    for fname,pages in docs.items():
        if selected_docs and Path(fname).name not in selected_docs:
            continue
        for p in pages:
            for s in p["sentences"]:
                all_sentences.append({"file":fname,"page_num":p["page_num"],"text":s,"image":p["image"]})
    if not all_sentences:
        return {}

    # Encode sentences
    corpus = [s["text"] for s in all_sentences]
    corpus_embeddings = MODEL.encode(corpus, convert_to_numpy=True)
    query_vec = MODEL.encode([query], convert_to_numpy=True)
    sims = cosine_similarity(query_vec, corpus_embeddings)[0]

    # Top sentences
    top_idx = sims.argsort()[::-1][:top_k]
    aligned = defaultdict(list)
    for idx in top_idx:
        s = all_sentences[idx]
        aligned[s["text"]].append(s)
    return aligned

# ---------------------------
# UI
# ---------------------------
CSS = """
body {font-family:Inter,sans-serif; background:#f5f7fa; color:#1a1a1a;}
h2 {margin-bottom:10px;}
.card {background:#fff; padding:12px; border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.1); margin-bottom:12px; display:flex; gap:12px;}
.card img {width:120px; border-radius:6px;}
.card div {flex:1;}
mark {background:#ffeeba; padding:0 2px;}
.comparison-row {display:flex; gap:10px;}
.comparison-cell {flex:1; background:#eef0f5; padding:8px; border-radius:6px;}
"""

def search_aligned_ui(files, query, doc_filter):
    if not files or not query.strip():
        return "Please upload files and enter a search term."
    docs = load_documents(files)
    selected_docs = doc_filter if doc_filter else None
    matches = aligned_related_search(query, docs, top_k=10, selected_docs=selected_docs)
    if not matches:
        return "No matches found."

    html = ""
    for sent, group in matches.items():
        html += "<div class='comparison-row'>"
        for m in group:
            img_tag = f"<img src='{m['image']}'/>" if m['image'] else ""
            html += f"<div class='comparison-cell'><strong>{Path(m['file']).name} - Page {m['page_num']}</strong><br>{img_tag}<br>{highlight_text(m['text'],[query])}</div>"
        html += "</div><hr/>"
    return html

# ---------------------------
# Gradio App
# ---------------------------
with gr.Blocks(css=CSS, title="Meeting Minutes Aligned Search") as demo:
    gr.Markdown("<h2>Aligned Meeting Minutes Search</h2><p>Search multiple documents. Results aligned by topic across documents.</p>")
    file_input = gr.File(file_types=[".pdf",".docx",".txt"], file_count="multiple")
    query = gr.Textbox(placeholder="Enter search term...")
    doc_filter = gr.CheckboxGroup([], label="Filter by Document")
    search_btn = gr.Button("Search")
    output = gr.HTML("<div>No results yet</div>")

    # Update doc_filter options dynamically based on uploaded files
    def update_doc_filter(files):
        return [Path(f).name for f in files] if files else []
    file_input.upload(update_doc_filter, file_input, doc_filter)

    search_btn.click(search_aligned_ui, inputs=[file_input, query, doc_filter], outputs=output)

if __name__=="__main__":
    demo.launch()
