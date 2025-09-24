import gradio as gr
import os
import zipfile
import docx
from PyPDF2 import PdfReader
import nltk
from nltk.corpus import wordnet
import re

# Ensure NLTK data
nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)

# -------------------------------
# Document Processing & Search
# -------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text += f"\n[PDF READ ERROR: {file_path} | {e}]"
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text += f"\n[DOCX READ ERROR: {file_path} | {e}]"
    return text

def extract_text_from_zip(file_path):
    text = ""
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".pdf"):
                    with z.open(name) as f:
                        tmp_path = f"/tmp/{os.path.basename(name)}"
                        with open(tmp_path, "wb") as tmpf:
                            tmpf.write(f.read())
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_pdf(tmp_path)
                elif name.lower().endswith(".docx"):
                    with z.open(name) as f:
                        tmp_path = f"/tmp/{os.path.basename(name)}"
                        with open(tmp_path, "wb") as tmpf:
                            tmpf.write(f.read())
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_docx(tmp_path)
    except Exception as e:
        text += f"\n[ZIP READ ERROR: {file_path} | {e}]"
    return text

def load_documents(files):
    all_texts = {}
    for file_path in files:
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            all_texts[file_path] = extract_text_from_pdf(file_path)
        elif lower.endswith(".docx"):
            all_texts[file_path] = extract_text_from_docx(file_path)
        elif lower.endswith(".zip"):
            all_texts[file_path] = extract_text_from_zip(file_path)
        else:
            all_texts[file_path] = f"[Unsupported file type: {file_path}]"
    return all_texts

def expand_query(query):
    expanded = {query.lower()}
    for syn in wordnet.synsets(query):
        for lemma in syn.lemmas():
            expanded.add(lemma.name().lower().replace("_", " "))
    return expanded

def highlight_text(text, keywords):
    for kw in sorted(keywords, key=len, reverse=True):
        regex = re.compile(rf"\b({re.escape(kw)})\b", re.IGNORECASE)
        text = regex.sub(r"<span class='highlight'>\1</span>", text)
    return text

def search_documents(files, query):
    if not files or not query.strip():
        return "<div class='no-results'>⚠️ Please upload documents and enter a search query.</div>"

    documents = load_documents(files)
    results = []

    keywords = expand_query(query)

    for fname, text in documents.items():
        if not text.strip():
            continue

        lines = text.split("\n")
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in keywords):
                snapshot = "\n".join(lines[max(0, i-1): min(len(lines), i+2)])
                highlighted = highlight_text(snapshot, keywords)
                results.append(
                    f"<div class='result-card'>"
                    f"<div class='result-header'>📄 <strong>{os.path.basename(fname)}</strong> — line {i+1}</div>"
                    f"<div class='result-snippet'>{highlighted}</div>"
                    f"</div>"
                )

    if not results:
        return f"<div class='no-results'>❌ No matches found for <strong>{query}</strong></div>"
    return "\n".join(results)

# -------------------------------
# Custom CSS (Light + Dark mode)
# -------------------------------
custom_css = r"""
:root {
    --bg-color: #f9f9f9;
    --text-color: #222;
    --card-bg: #fff;
    --highlight-bg: #fffc8c;
    --shadow: rgba(0,0,0,0.1);
}
.dark-mode {
    --bg-color: #121212;
    --text-color: #eee;
    --card-bg: #1e1e1e;
    --highlight-bg: #3f3f0a;
    --shadow: rgba(0,0,0,0.6);
}
.gradio-container {
    background-color: var(--bg-color);
    color: var(--text-color);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transition: background-color 0.3s, color 0.3s;
}
h1, h2, h3, label {
    color: var(--text-color);
}
.result-card {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px var(--shadow);
    transition: background 0.3s;
}
.result-header {
    font-size: 1.1em;
    margin-bottom: 8px;
}
.result-snippet {
    font-family: monospace;
    white-space: pre-wrap;
}
.highlight {
    background-color: var(--highlight-bg);
    padding: 2px 4px;
    border-radius: 3px;
}
.no-results {
    padding: 16px;
    font-size: 1.1em;
    color: var(--text-color);
}
.toggle-btn {
    float: right;
    margin-top: -60px;
    margin-right: 10px;
}
"""

# -------------------------------
# JS toggle for dark mode
# -------------------------------
toggle_js = """
function toggleTheme() {
    document.querySelector('.gradio-container').classList.toggle('dark-mode');
}
"""

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, js=toggle_js) as demo:
    gr.Markdown("<h1>🔍 Smart Document Search</h1>", elem_id="main-title")
    gr.Button("🌙 Toggle Dark Mode", elem_classes="toggle-btn", click=None, js="toggleTheme()")
    gr.Markdown("<p>Upload your PDFs, Word docs, or ZIP files. Search naturally, and get context-rich results.</p>")

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            type="filepath",
            file_types=[".pdf", ".docx", ".zip"],
            file_count="multiple"
        )

    with gr.Row():
        query = gr.Textbox(label="Search Query", placeholder="Type a word or phrase…")

    search_btn = gr.Button("Search", variant="primary")
    output = gr.HTML()

    search_btn.click(fn=search_documents, inputs=[file_input, query], outputs=output)

demo.launch()
