import os
import re
import tempfile
import zipfile
import pdfplumber
import docx
from pdf2image import convert_from_path
import pytesseract
from sentence_transformers import SentenceTransformer
import numpy as np
import gradio as gr

# -------------------------------
# Setup
# -------------------------------
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

# -------------------------------
# Document Processing
# -------------------------------
def extract_text_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text
    except:
        # fallback OCR
        images = convert_from_path(file_path)
        return "\n".join(pytesseract.image_to_string(img) for img in images)

def extract_text_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""

def extract_text_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def extract_text_from_zip(zip_path):
    texts = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.endswith((".pdf", ".docx", ".txt")):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(name)[1]) as tmp:
                    tmp.write(z.read(name))
                    tmp_path = tmp.name
                if name.endswith(".pdf"):
                    texts[name] = extract_text_pdf(tmp_path)
                elif name.endswith(".docx"):
                    texts[name] = extract_text_docx(tmp_path)
                elif name.endswith(".txt"):
                    texts[name] = extract_text_txt(tmp_path)
                os.remove(tmp_path)
    return texts

def load_documents(files):
    all_texts = {}
    for f in files:
        if f.endswith(".pdf"):
            all_texts[f] = extract_text_pdf(f)
        elif f.endswith(".docx"):
            all_texts[f] = extract_text_docx(f)
        elif f.endswith(".txt"):
            all_texts[f] = extract_text_txt(f)
        elif f.endswith(".zip"):
            all_texts.update(extract_text_from_zip(f))
    return all_texts

# -------------------------------
# Highlight matches
# -------------------------------
def highlight_sentence(sentence, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", sentence)

# -------------------------------
# Search Function
# -------------------------------
def search_docs(files, query):
    if not files or not query.strip():
        return "⚠️ Please upload documents and enter a search query."
    
    documents = load_documents(files)
    query_vec = MODEL.encode([query])[0]
    results = []

    for fname, text in documents.items():
        if not text.strip():
            continue
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sent_vecs = MODEL.encode(sentences)
        sims = np.dot(sent_vecs, query_vec) / (np.linalg.norm(sent_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-10)
        for i, score in enumerate(sims):
            if score > 0.55:  # threshold
                highlighted = highlight_sentence(sentences[i], query)
                results.append(f"### 📄 {os.path.basename(fname)}\n\n{highlighted}")

    if not results:
        return f"❌ No matches found for '{query}'."
    return "\n\n---\n\n".join(results)

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks(css="""
    #app-container {max-width: 1100px; margin: auto;}
    .upload-box {border: 2px dashed #bbb; padding: 30px; border-radius: 12px; text-align: center;}
    .search-box {margin-top: 20px;}
    .results-box {background: #fafafa; border-radius: 12px; padding: 20px; border: 1px solid #ddd;}
    h1 {font-size: 2em; margin-bottom: 10px;}
    h3 {margin-top: 20px;}
""") as demo:
    with gr.Column(elem_id="app-container"):
        gr.Markdown(
            """
            # 🔎 Document Search Tool
            Upload **PDFs, Word, TXT, or ZIP archives** of meeting minutes and search for keywords.  
            Matches are shown in context with highlights.
            """
        )

        file_input = gr.File(
            label="Upload Documents or ZIPs",
            file_types=[".pdf", ".docx", ".txt", ".zip"],
            file_count="multiple",
            type="filepath",
            elem_classes="upload-box"
        )

        query_input = gr.Textbox(
            label="Search Query",
            placeholder="Enter a word or phrase...",
            elem_classes="search-box"
        )

        search_button = gr.Button("Search", variant="primary")
        output = gr.Markdown(elem_classes="results-box")

        search_button.click(fn=search_docs, inputs=[file_input, query_input], outputs=output)

# -------------------------------
# Launch
# -------------------------------
if __name__ == "__main__":
    demo.launch()
