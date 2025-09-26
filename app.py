import os
import tempfile
import zipfile
from pathlib import Path
import PyPDF2
import docx
import gradio as gr

from sentence_transformers import SentenceTransformer, util

# -----------------------------
# AI Model for Embeddings
# -----------------------------
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# File Parsing
# -----------------------------
def extract_text_from_pdf(path):
    text = []
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                txt = page.extract_text() or ""
                text.append(txt)
    except Exception as e:
        text.append(f"[PDF parse error: {e}]")
    return "\n".join(text)


def extract_text_from_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[DOCX parse error: {e}]"


def process_zip(path, tmpdir):
    paths = []
    try:
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(tmpdir)
            for root, _, files in os.walk(tmpdir):
                for fname in files:
                    paths.append(os.path.join(root, fname))
    except Exception as e:
        print("Zip error:", e)
    return paths


# -----------------------------
# Global Store
# -----------------------------
CHUNKS = []  # list of dicts: {doc, text, embedding}


def upload_files(files):
    """Extract, chunk, and embed documents"""
    global CHUNKS
    CHUNKS.clear()

    tmpdir = tempfile.mkdtemp(prefix="uploads_")

    file_list = files if isinstance(files, list) else [files]
    for f in file_list:
        if not f:
            continue
        path = getattr(f, "name", None) or (f.get("name") if isinstance(f, dict) else None)
        if not path:
            continue

        if path.lower().endswith(".pdf"):
            text = extract_text_from_pdf(path)
        elif path.lower().endswith(".docx"):
            text = extract_text_from_docx(path)
        elif path.lower().endswith(".zip"):
            extracted = process_zip(path, tmpdir)
            for ep in extracted:
                if ep.lower().endswith(".pdf"):
                    text = extract_text_from_pdf(ep)
                    _chunk_and_embed(text, Path(ep).name)
                elif ep.lower().endswith(".docx"):
                    text = extract_text_from_docx(ep)
                    _chunk_and_embed(text, Path(ep).name)
            continue
        else:
            continue

        _chunk_and_embed(text, Path(path).name)

    return f"✅ Uploaded and embedded {len(CHUNKS)} text chunks."


def _chunk_and_embed(text, docname, chunk_size=400):
    """Split text into chunks and embed them"""
    global CHUNKS
    lines = text.split("\n")
    buf = []
    for line in lines:
        if not line.strip():
            continue
        buf.append(line.strip())
        if sum(len(x) for x in buf) > chunk_size:
            chunk = " ".join(buf)
            emb = MODEL.encode(chunk, convert_to_tensor=True)
            CHUNKS.append({"doc": docname, "text": chunk, "embedding": emb})
            buf = []
    if buf:
        chunk = " ".join(buf)
        emb = MODEL.encode(chunk, convert_to_tensor=True)
        CHUNKS.append({"doc": docname, "text": chunk, "embedding": emb})


# -----------------------------
# AI Search
# -----------------------------
def search_docs(query, top_k=5):
    global CHUNKS
    if not CHUNKS:
        return [gr.Textbox.update(value="⚠️ No documents uploaded yet.")]

    query_emb = MODEL.encode(query, convert_to_tensor=True)
    scores = [(util.cos_sim(query_emb, c["embedding"]).item(), c) for c in CHUNKS]
    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_k]

    results = []
    for score, chunk in scores:
        snippet = chunk["text"]
        results.append(
            gr.Textbox.update(
                value=f"📄 {chunk['doc']} (score: {score:.2f})\n\n{snippet}\n",
                label="Match"
            )
        )
    return results


# -----------------------------
# Gradio UI
# -----------------------------
with gr.Blocks(css=".gr-textbox {font-family: Arial; font-size: 14px;}") as demo:
    gr.Markdown("## 🤖 AI-Powered Meeting Minutes Search\nUpload PDFs, Word docs, or ZIP files, then search semantically for key topics.")

    with gr.Row():
        upload_box = gr.File(
            label="Upload Documents (PDF, DOCX, ZIP)",
            file_types=[".pdf", ".docx", ".zip"],
            type="file",
            file_types="file"
        )
        upload_btn = gr.Button("Process Uploads", variant="primary")

    status = gr.Textbox(label="Status", interactive=False)

    with gr.Row():
        query = gr.Textbox(label="Search term", placeholder="e.g. animal")
        search_btn = gr.Button("Search", variant="primary")

    results = gr.Group()

    upload_btn.click(upload_files, inputs=upload_box, outputs=status)
    search_btn.click(search_docs, inputs=query, outputs=results)

if __name__ == "__main__":
    demo.launch()
