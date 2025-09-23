# app.py
# Single-file Gradio app: upload PDFs/DOCX or a ZIP of folders -> process all files -> search keywords
import gradio as gr
import fitz       # pip install pymupdf
import docx       # pip install python-docx
import os, zipfile, tempfile, shutil, re

# In-memory store for this session: {relative_path: {"text":..., "note":...}}
DOCS = {}

def extract_text_pdf(path):
    try:
        text = ""
        with fitz.open(path) as pdf:
            for page in pdf:
                text += page.get_text("text") or ""
        return text
    except Exception as e:
        return ""  # handle gracefully

def extract_text_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return ""

def process_upload(filepaths):
    """
    filepaths: list of local paths (Gradio provides actual file paths when type="filepath")
    This extracts ZIPs (if any), copies other files into a temporary workspace, and scans for pdf/docx.
    """
    global DOCS
    DOCS.clear()
    tmp = tempfile.mkdtemp(prefix="docsearch_")
    processed = []
    errors = []

    if not filepaths:
        return "No files uploaded. Upload PDFs/DOCX files or a ZIP containing folders."

    # 1) copy or extract uploaded items into tmp
    for p in filepaths:
        if not p:
            continue
        p = str(p)
        if not os.path.exists(p):
            errors.append(f"File not found: {p}")
            continue
        if p.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(p, "r") as z:
                    z.extractall(tmp)
            except Exception as e:
                errors.append(f"Failed to extract {os.path.basename(p)}: {e}")
        else:
            try:
                shutil.copy(p, os.path.join(tmp, os.path.basename(p)))
            except Exception as e:
                errors.append(f"Failed to copy {os.path.basename(p)}: {e}")

    # 2) walk tmp and process pdf/docx
    for root, dirs, files in os.walk(tmp):
        for fname in files:
            low = fname.lower()
            if low.endswith(".pdf") or low.endswith(".docx"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, tmp)
                try:
                    if low.endswith(".pdf"):
                        text = extract_text_pdf(full)
                    else:
                        text = extract_text_docx(full)
                    note = ""
                    if not text.strip():
                        note = "(no text extracted — likely a scanned PDF or protected file)"
                    DOCS[rel] = {"text": text, "note": note, "path": full}
                    processed.append(rel)
                except Exception as e:
                    errors.append(f"{rel}: {e}")

    # 3) Prepare status message (Markdown)
    md = f"**Processed {len(processed)} document(s).**\n\n"
    if processed:
        md += "### Documents found\n"
        for p in processed:
            note = DOCS[p]["note"]
            md += f"- **{p}** {note}\n"
    else:
        md += "No PDF or DOCX files were found in the upload or ZIP.\n"

    if errors:
        md += "\n### Warnings / errors\n"
        for e in errors:
            md += f"- {e}\n"

    md += "\n**Notes:**\n- If a PDF shows “no text extracted” it is probably a scanned image PDF. OCR is not included here but I can add it (tesseract) if you want.\n- To upload folder trees from your machine, compress the folder(s) to a ZIP and upload the ZIP.\n"
    return md

def search_docs(keyword):
    """
    Search across in-memory DOCS and return HTML results with snippets and highlights.
    """
    if not keyword or not keyword.strip():
        return "<p style='color:orange;'>Enter a keyword or phrase to search.</p>"
    k = keyword.strip()
    k_esc = re.escape(k)
    results_html = f"<h3>Search results for: <em>{k}</em></h3>"
    found = False
    for fname, info in DOCS.items():
        text = info["text"] or ""
        if not text:
            continue
        lower = text.lower()
        matches = list(re.finditer(re.escape(k.lower()), lower))
        if matches:
            found = True
            results_html += f"<h4>{fname} — {len(matches)} hit(s)</h4><ul>"
            # show up to 5 snippets per file
            for m in matches[:5]:
                s = m.start()
                e = m.end()
                start = max(0, s-120)
                end = min(len(text), e+120)
                snippet = text[start:end].replace("\n", " ")
                # highlight occurrences (case-insensitive)
                snippet_html = re.sub(r"(?i)"+k_esc, lambda m: f"<mark>{m.group(0)}</mark>", snippet)
                results_html += f"<li>... {snippet_html} ...</li>"
            if len(matches) > 5:
                results_html += f"<li>...and {len(matches)-5} more matches...</li>"
            results_html += "</ul>"
    if not found:
        results_html += "<p>No matches found.</p>"
    return results_html

def clear_docs():
    DOCS.clear()
    return "Cleared stored documents. Upload new files to start."

# --- Gradio UI ---
with gr.Blocks(title="Document Batch Search") as demo:
    gr.Markdown(
        """
        # Document Batch Search (PDF / DOCX / ZIP)
        Upload PDF or DOCX files **or** a ZIP containing folder(s) with PDFs/DOCX.
        The app will extract text and allow fast keyword searches across the entire upload.
        **Notes:** ZIP is the easiest way to upload a folder tree. Scanned PDFs will need OCR (not included).
        """
    )

    with gr.Row():
        upload = gr.File(label="Upload files or ZIP (multiple)", file_count="multiple",
                         file_types=[".pdf", ".docx", ".zip"], type="filepath")
        proc_btn = gr.Button("Process uploads")

    status_md = gr.Markdown("No files processed yet.")
    proc_btn.click(fn=process_upload, inputs=[upload], outputs=[status_md])

    with gr.Row():
        keyword = gr.Textbox(label="Search keyword or phrase", placeholder="Enter keyword or phrase to search...")
        search_btn = gr.Button("Search")

    results = gr.HTML("<p>No search performed yet.</p>")
    search_btn.click(fn=search_docs, inputs=[keyword], outputs=[results])

    with gr.Row():
        clear_btn = gr.Button("Clear stored documents")
        clear_btn.click(fn=clear_docs, inputs=None, outputs=[status_md])

    gr.Markdown(
        """
        **How to use (tips):**
        - To upload entire folders, compress them into a ZIP on your machine and upload the ZIP.
        - If the PDF is a scan (image), the app will not extract text — ask me and I can add OCR (Tesseract).
        - For Hugging Face Spaces: create a *Gradio* Space and add this `app.py`. Add a `requirements.txt` with dependencies:
        ```
        gradio
        pymupdf
        python-docx
        ```
        """
    )

if __name__ == "__main__":
    demo.launch()
