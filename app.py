# improved_gradio_app.py
import gradio as gr
import os
import zipfile
import docx
from PyPDF2 import PdfReader
import nltk
from nltk.corpus import wordnet
import re
import html
from pathlib import Path

# --- Try to ensure NLTK is available but do not crash if offline ---
try:
    nltk.data.find("corpora/wordnet")
except Exception:
    try:
        nltk.download("wordnet", quiet=True)
    except Exception:
        # fallback: wordnet won't be available; synonym expansion becomes a no-op
        pass

# -------------------------------
# Document Processing (unchanged logic but resilient)
# -------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception as e:
        text += f"\n[PDF READ ERROR: {file_path} | {e}]\n"
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text += f"\n[DOCX READ ERROR: {file_path} | {e}]\n"
    return text

def extract_text_from_zip(file_path):
    text = ""
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".pdf") or name.lower().endswith(".docx"):
                    # extract to a temp path in current dir's .tmp
                    tmp_dir = Path(".tmp")
                    tmp_dir.mkdir(exist_ok=True)
                    tmp_path = tmp_dir / Path(name).name
                    tmp_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(tmp_path, "wb") as tmpf:
                        tmpf.write(z.read(name))
                    if name.lower().endswith(".pdf"):
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_pdf(tmp_path)
                    else:
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_docx(tmp_path)
    except Exception as e:
        text += f"\n[ZIP READ ERROR: {file_path} | {e}]\n"
    return text

def load_documents(files):
    all_texts = {}
    for file_path in files:
        if file_path.lower().endswith(".pdf"):
            all_texts[file_path] = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(".docx"):
            all_texts[file_path] = extract_text_from_docx(file_path)
        elif file_path.lower().endswith(".zip"):
            all_texts[file_path] = extract_text_from_zip(file_path)
        else:
            all_texts[file_path] = f"[Unsupported file type: {file_path}]"
    return all_texts

# -------------------------------
# Search helpers
# -------------------------------
def expand_query(query):
    """Expand search query to include synonyms; if wordnet missing, return query only."""
    q = query.strip().lower()
    expanded = {q}
    try:
        for syn in wordnet.synsets(q):
            for lemma in syn.lemmas():
                expanded.add(lemma.name().lower().replace("_", " "))
    except Exception:
        # wordnet may not be available in offline environments
        pass
    return expanded

def html_escape(s):
    return html.escape(s, quote=False)

def highlight_html(text, keywords):
    """Replace matches with <mark> ... </mark>. Case-insensitive."""
    # escape first
    escaped = html_escape(text)
    # build regex of keywords (longer first)
    kws = sorted(set(keywords), key=len, reverse=True)
    for kw in kws:
        if not kw.strip():
            continue
        # create case-insensitive regex; we must operate on escaped text so we use re.IGNORECASE
        pattern = re.compile(rf"(?i)\b({re.escape(kw)})\b")
        escaped = pattern.sub(r"<mark>\1</mark>", escaped)
    # preserve simple line breaks
    return escaped.replace("\n", "<br>")

# -------------------------------
# Search Function (returns HTML)
# -------------------------------
def search_documents(files, query, use_synonyms=True, context_lines=1):
    if not files or not query.strip():
        return "<div class='notice'>Please upload documents and enter a search query.</div>"

    documents = load_documents(files)
    keywords = expand_query(query) if use_synonyms else {query.strip().lower()}

    results_html = []
    total_matches = 0

    for fname, text in documents.items():
        if not text or not text.strip():
            continue

        lines = text.split("\n")
        for i, line in enumerate(lines):
            # check existence
            if any(kw in line.lower() for kw in keywords):
                total_matches += 1
                # context window
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snapshot = "\n".join(lines[start:end])
                highlighted = highlight_html(snapshot, keywords)
                card = f"""
                <div class="result-card">
                  <div class="result-meta">
                    <div class="fname">{html_escape(Path(fname).name)}</div>
                    <div class="line">Line {i+1}</div>
                  </div>
                  <div class="snippet">{highlighted}</div>
                </div>
                """
                results_html.append(card)

    if not results_html:
        return f"<div class='notice'>No matches found for: <strong>{html_escape(query)}</strong></div>"

    header = f"<div class='summary'>Found {total_matches} matches across {len(documents)} document(s)</div>"
    return header + "<div class='results-grid'>" + "".join(results_html) + "</div>"

# -------------------------------
# Polished CSS for the app
# -------------------------------
CUSTOM_CSS = """
/* Layout */
.app-row{ display:flex; gap:20px; align-items:flex-start; }
.left-col{ width:360px; min-width:300px; }
.right-col{ flex:1; }

/* File list */
.file-list { margin-top:12px; display:flex; flex-direction:column; gap:8px; }
.file-item { background:var(--background-secondary); border-radius:8px; padding:10px; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 1px 0 rgba(0,0,0,0.03); }
.file-meta { display:flex; flex-direction:column; gap:2px; font-size:13px; }
.file-actions { display:flex; gap:8px; align-items:center; }

/* Results */
.results-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap:12px; margin-top:12px; }
.result-card { border-radius:8px; padding:12px; background:linear-gradient(180deg, #ffffff, #fbfbfb); box-shadow: 0 6px 18px rgba(16,24,40,0.04); border:1px solid rgba(16,24,40,0.04); }
.result-meta { display:flex; justify-content:space-between; font-weight:600; margin-bottom:8px; font-size:13px; color: #0f172a; }
.snippet { font-size:13px; color:#0b1220; line-height:1.35; max-height:7.5em; overflow:hidden; }
mark { background: #fff59d; padding:0 2px; border-radius:3px; }

/* Notices */
.notice { padding:12px; border-radius:8px; background:#fff4e6; color:#6a4b1b; }

/* Buttons and controls */
.control-row { display:flex; gap:8px; align-items:center; margin-top:8px; }
.small { font-size:13px; padding:6px 10px; }

/* responsive */
@media (max-width:900px){
  .app-row{ flex-direction:column; }
  .left-col{ width:100%; }
}
"""

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Soft()) as demo:
    gr.Markdown("<h2>Smart Document Search</h2><p>Upload PDFs, Word files, or ZIPs and search across them. Use the synonym toggle to include related words in results.</p>")

    with gr.Row(elem_classes="app-row"):
        with gr.Column(elem_classes="left-col"):
            file_input = gr.File(label="Upload documents (PDF, DOCX, ZIP)", file_count="multiple", file_types=[".pdf", ".docx", ".zip"], elem_id="uploader")
            files_preview = gr.HTML("<div class='file-list' id='file-list-placeholder'></div>")
        with gr.Column(elem_classes="right-col"):
            query = gr.Textbox(label="Search query", placeholder="Enter a word or phrase...", lines=1)
            with gr.Row(elem_classes="control-row"):
                synonym_toggle = gr.Checkbox(label="Include synonyms (WordNet)", value=True)
                context_slider = gr.Slider(label="Context lines", minimum=0, maximum=5, step=1, value=1)
                search_btn = gr.Button("Search", variant="primary", elem_id="search-btn")
            results = gr.HTML()

    # Update file preview on upload (client-side rendering of filenames and sizes)
    def render_file_list(files):
        if not files:
            return "<div class='file-list'><div class='file-item'>No files uploaded</div></div>"
        items = []
        for f in files:
            # in gradio filepath mode f is a path
            try:
                size = Path(f).stat().st_size
                size_kb = f"{size//1024} KB"
            except Exception:
                size_kb = "—"
            items.append(f"""
                <div class='file-item'>
                  <div class='file-meta'>
                    <div><strong>{html_escape(Path(f).name)}</strong></div>
                    <div style='color:var(--text-secondary); font-size:12px;'>{size_kb} • {html_escape(str(Path(f).suffix).lower())}</div>
                  </div>
                  <div class='file-actions'>
                    <button class='small' onclick="(function(){{
                      // no-op: actual remove handled server-side if needed
                    }})();">Remove</button>
                  </div>
                </div>
            """)
        return "<div class='file-list'>" + "".join(items) + "</div>"

    file_input.upload(fn=render_file_list, inputs=file_input, outputs=files_preview)

    def on_search(files, q, synonyms, context):
        return search_documents(files or [], q or "", use_synonyms=bool(synonyms), context_lines=int(context))

    search_btn.click(fn=on_search, inputs=[file_input, query, synonym_toggle, context_slider], outputs=results)

if __name__ == "__main__":
    demo.launch(debug=True)
