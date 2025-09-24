import gradio as gr
from PyPDF2 import PdfReader
import docx
import zipfile
import io
import os
import nltk
from nltk.corpus import wordnet
from rapidfuzz import fuzz

# Ensure NLTK wordnet data is downloaded
nltk.download("wordnet", quiet=True)

# ------------------------------
# Helpers
# ------------------------------
def highlight(text, query):
    """Highlight query-like terms in snippet."""
    # Bold matches of query words
    return text.replace(query, f"**{query}**")

def is_similar(text, query):
    """Check if a line is similar enough (smart fuzzy matching)."""
    return fuzz.partial_ratio(query.lower(), text.lower()) >= 70

def expand_query(query):
    """Expand with synonyms (WordNet)."""
    synonyms = set([query])
    for syn in wordnet.synsets(query):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))
    return list(synonyms)

# ------------------------------
# File Readers
# ------------------------------
def read_pdf(file_obj):
    pdf = PdfReader(file_obj)
    text = ""
    for page in pdf.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def read_docx(file_obj):
    doc = docx.Document(file_obj)
    return "\n".join([p.text for p in doc.paragraphs])

def read_zip(file_path):
    text = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                if name.endswith(".pdf"):
                    with zip_ref.open(name) as f:
                        text.append(read_pdf(io.BytesIO(f.read())))
                elif name.endswith(".docx"):
                    with zip_ref.open(name) as f:
                        text.append(read_docx(io.BytesIO(f.read())))
    except Exception as e:
        text.append(f"❌ Could not read ZIP: {e}")
    return "\n\n---\n\n".join(text)

# ------------------------------
# Search Functions
# ------------------------------
def search_pdf(file_path, query, context_chars=50):
    results = []
    try:
        pdf = PdfReader(file_path)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            for line in text.split("\n"):
                if is_similar(line, query):
                    idx = line.lower().find(query.lower())
                    start = max(idx - context_chars, 0) if idx != -1 else 0
                    end = start + context_chars * 2
                    snippet = line[start:end].strip()
                    snippet = highlight(snippet, query)
                    file_url = f"file://{os.path.abspath(file_path)}#page={i+1}"
                    results.append(
                        f"### 📄 {os.path.basename(file_path)} — Page {i+1}\n"
                        f"[🔗 Open PDF at this page]({file_url})\n\n"
                        f"> {snippet}"
                    )
    except Exception as e:
        results.append(f"❌ Could not search PDF: {e}")
    return results

def search_docx(file_path, query, context_chars=50):
    results = []
    try:
        doc = docx.Document(file_path)
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if is_similar(text, query):
                idx = text.lower().find(query.lower())
                start = max(idx - context_chars, 0) if idx != -1 else 0
                end = start + context_chars * 2
                snippet = text[start:end]
                snippet = highlight(snippet, query)
                results.append(
                    f"### 📝 {os.path.basename(file_path)} — Paragraph {i+1}\n"
                    f"> {snippet}"
                )
    except Exception as e:
        results.append(f"❌ Could not search DOCX: {e}")
    return results

def process_search(files, query, use_synonyms):
    if not files or not query:
        return "⚠️ Please upload files and enter a search query."

    all_results = []
    queries = [query]

    if use_synonyms:
        queries = expand_query(query)

    for file_path in files:
        ext = os.path.splitext(file_path)[1].lower()
        for q in queries:
            if ext == ".pdf":
                all_results.extend(search_pdf(file_path, q))
            elif ext == ".docx":
                all_results.extend(search_docx(file_path, q))
            elif ext == ".zip":
                # TODO: Expand ZIP fuzzy search here if needed
                all_results.append("🔒 Searching inside ZIP archives coming soon.")
            else:
                all_results.append(f"⚠️ Unsupported file type: {ext}")

    if not all_results:
        return "❌ No matches found."

    return "\n\n---\n\n".join(all_results)

# ------------------------------
# Gradio UI
# ------------------------------
with gr.Blocks(theme="soft") as demo:
    gr.Markdown("# 🔎 Document Search")
    gr.Markdown(
        "Upload your **PDFs, Word docs, or ZIPs** and search naturally. "
        "No exact wording required — we'll find close matches and variations for you."
    )

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="📂 Upload Documents",
                file_types=[".pdf", ".docx", ".zip"],
                file_types_multiple=True,
                type="filepath"
            )
            search_query = gr.Textbox(label="🔍 Search Query", placeholder="e.g. contract deadlines, safety policy...")
            with gr.Accordion("⚙️ Advanced Options", open=False):
                use_synonyms = gr.Checkbox(label="Also search synonyms (WordNet)", value=False)
            search_btn = gr.Button("🚀 Search Documents", variant="primary")
        with gr.Column(scale=2):
            search_output = gr.Markdown("ℹ️ Results will appear here...")

    search_btn.click(
        process_search,
        inputs=[file_input, search_query, use_synonyms],
        outputs=search_output,
    )

demo.launch()
