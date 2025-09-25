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
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

# ---------------------------
# Initialization
# ---------------------------
MODEL = SentenceTransformer("all-MiniLM-L6-v2")
IMG_CACHE = Path("page_images")
IMG_CACHE.mkdir(exist_ok=True)
THUMB_CACHE = Path("thumbnails")
THUMB_CACHE.mkdir(exist_ok=True)

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
# Document Thumbnails
# ---------------------------
def generate_pdf_thumbnail(pdf_path:str, width=200, height=150) -> str:
    key = sha1(pdf_path)+"_thumb.png"
    thumb_path = THUMB_CACHE / key
    if thumb_path.exists(): return str(thumb_path)
    pages = convert_from_path(pdf_path, first_page=1, last_page=1)
    img = pages[0]
    img.thumbnail((width,height))
    img.save(thumb_path)
    return str(thumb_path)

def generate_docx_thumbnail(docx_path:str, width=200, height=150) -> str:
    key = sha1(docx_path)+"_thumb.png"
    thumb_path = THUMB_CACHE / key
    if thumb_path.exists(): return str(thumb_path)
    doc = Document(docx_path)
    text = "\n".join([p.text for p in doc.paragraphs[:3]]) or "DOCX Document"
    img = Image.new("RGB", (width, height), color=(245,245,245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    draw.multiline_text((10,10), text, fill=(0,0,0), font=font)
    img.save(thumb_path)
    return str(thumb_path)

def get_thumbnail(file_path:str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return generate_pdf_thumbnail(file_path)
    elif ext == ".docx":
        return generate_docx_thumbnail(file_path)
    else:
        return "/static/file_icon.png"

def build_document_cards(file_objs):
    html = "<div class='card-container'>"
    for f in file_objs:
        thumb_src = get_thumbnail(f['name'])
        html += f"<div class='card'><img src='{thumb_src}'><strong>{Path(f['name']).name}</strong></div>"
    html += "</div>"
    return html

# ---------------------------
# Document Extraction
# ---------------------------
def extract_pdf_pages(pdf_path: str) -> List[Dict]:
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, p in enumerate(pdf.pages):
                text = p.extract_text() or ""
                if not text.strip():
                    img = p.to_image(resolution=300).original
                    text = pytesseract.image_to_string(img)
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
                img_path = save_pdf_page_image(pdf_path, i+1)
                pages.append({"page_num":i+1,"text":text,"sentences":sentences,"image":img_path})
    except Exception as e:
        print(f"PDF Error ({pdf_path}): {e}")
    return pages

def extract_docx_pages(docx_path: str, chunk_size:int=2000) -> List[Dict]:
    pages = []
    try:
        doc = Document(docx_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        i, page_num = 0, 1
        while i < len(text):
            chunk = text[i:i+chunk_size]
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk) if s.strip()]
            pages.append({"page_num":page_num,"text":chunk,"sentences":sentences,"image":None})
            i += chunk_size
            page_num += 1
    except Exception as e:
        print(f"DOCX Error ({docx_path}): {e}")
    return pages

def extract_txt(file_path:str) -> List[Dict]:
    pages = []
    try:
        text = Path(file_path).read_text(encoding="utf8")
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        pages.append({"page_num":1,"text":text,"sentences":sentences,"image":None})
    except Exception as e:
        print(f"TXT Error ({file_path}): {e}")
    return pages

def load_documents(file_objs:List[dict]) -> Dict[str,List[Dict]]:
    docs = {}
    for f in file_objs:
        path = f["name"] if "name" in f else f
        if path.lower().endswith(".pdf"):
            docs[path] = extract_pdf_pages(f["name"])
        elif path.lower().endswith(".docx"):
            docs[path] = extract_docx_pages(f["name"])
        elif path.lower().endswith(".txt"):
            docs[path] = extract_txt(f["name"])
    return docs

# ---------------------------
# Semantic Search
# ---------------------------
def aligned_related_search(query:str, docs:Dict[str,List[Dict]], top_k:int=15, selected_docs:List[str]=None) -> Dict[str,List[Dict]]:
    all_sentences = []
    for fname,pages in docs.items():
        if selected_docs and Path(fname).name not in selected_docs:
            continue
        for p in pages:
            for s in p["sentences"]:
                all_sentences.append({"file":fname,"page_num":p["page_num"],"text":s,"image":p["image"]})
    if not all_sentences:
        return {}

    corpus = [s["text"] for s in all_sentences]
    corpus_embeddings = MODEL.encode(corpus, convert_to_numpy=True)
    query_vec = MODEL.encode([query], convert_to_numpy=True)
    sims = cosine_similarity(query_vec, corpus_embeddings)[0]

    top_idx = sims.argsort()[::-1][:top_k]
    aligned = defaultdict(list)
    for idx in top_idx:
        s = all_sentences[idx]
        aligned[s["text"]].append(s)
    return aligned

# ---------------------------
# Professional PDF Export
# ---------------------------
class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.set_text_color(0, 0, 80)
        self.cell(0, 10, "Meeting Minutes Search Report", align="C", ln=True)
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def export_pdf_pro(matches:Dict[str,List[Dict]], query:str, filename="aligned_report.pdf"):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0,0,0)
    pdf.multi_cell(0, 8, f"Search Term: {query}\n\n")
    
    for sent, group in matches.items():
        for m in group:
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(0,0,120)
            pdf.multi_cell(0, 7, f"{Path(m['file']).name} - Page {m['page_num']}")
            pdf.ln(1)
            pdf.set_font("Arial", "", 12)
            text = m['text']
            for kw in [query]:
                text = re.sub(f"(?i)({re.escape(kw)})", r"<<\1>>", text)
            parts = text.split("<<")
            for part in parts:
                if ">>" in part:
                    kw, rest = part.split(">>",1)
                    pdf.set_text_color(255,0,0)
                    pdf.multi_cell(0, 6, kw)
                    pdf.set_text_color(0,0,0)
                    pdf.multi_cell(0, 6, rest)
                else:
                    pdf.multi_cell(0, 6, part)
            pdf.ln(2)
            if m['image']:
                try:
                    pdf.image(m['image'], w=100)
                    pdf.ln(2)
                except:
                    pass
            pdf.ln(3)
    pdf.output(filename)
    return filename

# ---------------------------
# UI Function
# ---------------------------
CSS = """
body {font-family:'Inter',sans-serif; background:#f4f6f8; color:#1a1a1a;}
h2 {margin-bottom:10px;}
#search-section {background:#fff; padding:20px; border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.05);}
.card-container {display:flex; flex-wrap:wrap; gap:16px; margin-top:10px;}
.card {background:#fff; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.1); padding:12px; width:200px; text-align:center;}
.card img {width:100%; height:120px; object-fit:cover; border-radius:8px;}
.card strong {display:block; margin-top:8px; font-size:14px;}
.comparison-row {display:flex; gap:12px; flex-wrap:wrap;}
.comparison-cell {position:relative; flex:1; background:#ffffff; padding:12px; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.05); min-width:250px; transition: transform 0.2s;}
.comparison-cell:hover {transform: scale(1.02); z-index:10;}
.preview-image {display:none; position:absolute; top:-10px; left:105%; width:300px; max-height:400px; border:2px solid #ccc; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.3); background:#fff; padding:4px;}
.comparison-cell:hover .preview-image {display:block;}
mark {background:#ffeeba; padding:0 2px;}
"""

def search_and_export_ui(file_objs, query, doc_filter):
    if not file_objs or not query.strip():
        return "Please upload files and enter a search term.", None, build_document_cards(file_objs)
    
    docs = load_documents(file_objs)
    selected_docs = doc_filter if doc_filter else None
    matches = aligned_related_search(query, docs, top_k=15, selected_docs=selected_docs)
    if not matches:
        return "No matches found.", None, build_document_cards(file_objs)

    html = ""
    for sent, group in matches.items():
        html += "<div class='comparison-row'>"
        for m in group:
            preview_tag = f"<img src='{m['image']}' class='preview-image'/>" if m['image'] else ""
            html += f"<div class='comparison-cell'><strong>{Path(m['file']).name} - Page {m['page_num']}</strong><br>{highlight_text(m['text'],[query])}{preview_tag}</div>"
        html += "</div><hr/>"

    pdf_path = export_pdf_pro(matches, query)
    cards_html = build_document_cards(file_objs)
    return html, pdf_path, cards_html

# ---------------------------
# Launch Gradio App
# ---------------------------
with gr.Blocks(css=CSS, title="Meeting Minutes Aligned Search") as demo:
    gr.Markdown("<h2>Meeting Minutes Search</h2><p>Upload multiple documents, search across them, and export a professional PDF report.</p>")
    
    with gr.Row(elem_id="search-section"):
        file_input = gr.File(file_types=[".pdf",".docx",".txt"], file_count="multiple", label="Upload Documents")
        query = gr.Textbox(placeholder="Enter search term...", label="Search Query")
        doc_filter = gr.CheckboxGroup([], label="Filter by Document")
        search_btn = gr.Button("Search & Export PDF")
    
    output_html = gr.HTML("<div>No results yet</div>")
    pdf_download = gr.File(label="Download PDF")
    doc_cards = gr.HTML("<div>Uploaded documents will appear here</div>")

    # Update doc_filter dynamically
    def update_doc_filter(files):
        if not files: return []
        return [Path(f['name']).name for f in files]
    file_input.upload(update_doc_filter, file_input, doc_filter)

    search_btn.click(search_and_export_ui, inputs=[file_input, query, doc_filter],
                     outputs=[output_html, pdf_download, doc_cards])

if __name__ == "__main__":
    demo.launch()
