import gradio as gr
from PyPDF2 import PdfReader
import docx
import zipfile
import os
import nltk
from rapidfuzz import fuzz

# Download NLTK wordnet data if missing
from nltk.corpus import wordnet
try:
    wordnet.synsets("test")
except:
    nltk.download("wordnet")

# ------------------------------
# Helper functions
# ------------------------------
def highlight(text, query):
    import re
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)

def is_similar(text, query, threshold=75):
    """
    Returns True if the line/paragraph is similar to the query.
    threshold: similarity threshold (0-100)
    """
    return fuzz.partial_ratio(text.lower(), query.lower()) >= threshold

# ------------------------------
# Search functions
# ------------------------------
def search_pdf(file_path, query, context_chars=50, threshold=75):
    results = []
    try:
        pdf = PdfReader(file_path)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            for line in text.split("\n"):
                if is_similar(line, query, threshold):
                    idx = line.lower().find(query.lower())
                    # If exact substring not found, just show start of line
                    start = max(idx - context_chars, 0) if idx >=0 else 0
                    end = min(idx + len(query) + context_chars, len(line)) if idx >=0 else min(context_chars*2, len(line))
                    snippet = line[start:end].strip()
                    snippet = highlight(snippet, query)
                    file_url = f"file://{os.path.abspath(file_path)}#page={i+1}"
                    results.append(f"[{os.path.basename(file_path)} | Page {i+1}]({file_url})\n...{snippet}...")
    except Exception as e:
        results.append(f"[PDF READ ERROR: {file_path} | {e}]")
    return results

def search_docx(file_path, query, context_chars=50, threshold=75):
    results = []
    try:
        doc = docx.Document(file_path)
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if is_similar(text, query, threshold):
                idx = text.lower().find(query.lower())
                start = max(idx - context_chars, 0) if idx >=0 else 0
                end = min(idx + len(query) + context_chars, len(text)) if idx >=0 else min(context_chars*2, len(text))
                snippet = text[start:end]
                snippet = highlight(snippet, query)
                results.append(f"File: {os.path.basename(file_path)} | Paragraph: {i+1}\n...{snippet}...")
    except Exception as e:
        results.append(f"[DOCX READ ERROR: {file_path} | {e}]")
    return results

def search_zip(file_path, query, context_chars=50, threshold=75):
    results = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                temp_path = f"/tmp/{os.path.basename(name)}"
                with zip_ref.open(name) as f, open(temp_path, "wb") as tmp:
                    tmp.write(f.read())
                ext = os.path.splitext(name)[1].lower()
                if ext == ".pdf":
                    results.extend(search_pdf(temp_path, query, context_chars, threshold))
                elif ext == ".docx":
                    results.extend(search_docx(temp_path, query, context_chars, threshold))
                else:
                    results.append(f"[Unsupported file inside ZIP: {name}]")
    except Exception as e:
        results.append(f"[ZIP READ ERROR: {file_path} | {e}]")
    return results

def search_in_files(files, query, threshold=75):
    if not files or not query:
        return "[No files uploaded or search query is empty]"

    results = []
    for file_path in files:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            results.extend(search_pdf(file_path, query, threshold=threshold))
        elif ext == ".docx":
            results.extend(search_docx(file_path, query, threshold=threshold))
        elif ext == ".zip":
            results.extend(search_zip(file_path, query, threshold=threshold))
        else:
            results.append(f"[Unsupported file type: {ext}]")

    if not results:
        return "[No matches found]"
    return "\n\n".join(results)

# ------------------------------
# Gradio UI
# ------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 🔍 Fuzzy Document Search Tool")
    gr.Markdown(
        """
        Upload PDF, DOCX, or ZIP files (containing PDFs/DOCXs).  
        Search for a keyword or phrase and see contextual snippets with file references and locations.  
        PDF results include clickable links to the page. DOCX results show paragraph numbers.  
        The search term is highlighted in **bold**.  
        Fuzzy search allows finding similar words, partial matches, or minor typos.
        """
    )

    search_files = gr.File(
        label="Upload Documents",
        file_count="multiple",
        file_types=[".pdf", ".docx", ".zip"],
        type="filepath"
    )
    search_query = gr.Textbox(label="Search Query")
    threshold_slider = gr.Slider(label="Similarity Threshold (%)", minimum=50, maximum=100, value=75, step=1)
    search_output = gr.Markdown(label="Search Results", elem_id="search-results")
    search_btn = gr.Button("Search")
    search_btn.click(search_in_files, inputs=[search_files, search_query, threshold_slider], outputs=search_output)

demo.launch()
