import os
import re
import pdfplumber
import docx
from pdf2image import convert_from_path
import pytesseract
from sentence_transformers import SentenceTransformer
import numpy as np
import gradio as gr
from PIL import Image

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
        # fallback OCR if pdfplumber fails
        images = convert_from_path(file_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text

def extract_text_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""

def load_documents(files):
    all_texts = {}
    for f in files:
        if f.endswith(".pdf"):
            all_texts[f] = extract_text_pdf(f)
        elif f.endswith(".docx"):
            all_texts[f] = extract_text_docx(f)
        elif f.endswith(".txt"):
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                all_texts[f] = file.read()
        else:
            all_texts[f] = ""
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
        return "Upload documents and enter a search query."
    
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
            if score > 0.5:
                highlighted = highlight_sentence(sentences[i], query)
                results.append(f"**{os.path.basename(fname)}**:\n{highlighted}")

    if not results:
        return f"No matches found for '{query}'"
    return "\n\n---\n\n".join(results)

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown(
        """
        # 📑 Meeting Minutes Search
        Upload PDFs, Word (.docx), or TXT files and search for sentences.  
        Matches are highlighted for easy review.
        """
    )

    file_input = gr.File(
        label="Upload Documents",
        file_types=[".pdf", ".docx", ".txt"],
        file_count="multiple",
        type="filepath"
    )
    query_input = gr.Textbox(label="Search Query", placeholder="Enter word or phrase...")
    search_button = gr.Button("Search")
    output = gr.Markdown()

    search_button.click(fn=search_docs, inputs=[file_input, query_input], outputs=output)

# -------------------------------
# Launch
# -------------------------------
if __name__ == "__main__":
    demo.launch()
