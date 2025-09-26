import gradio as gr
import os
import zipfile
import docx
from PyPDF2 import PdfReader

# -------------------------------
# File Extractors
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

def extract_text_from_txt(file_path):
    text = ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        text += f"\n[TXT READ ERROR: {file_path} | {e}]"
    return text

def extract_text_from_zip(file_path):
    text = ""
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".pdf"):
                    tmp_path = f"/tmp/{os.path.basename(name)}"
                    with open(tmp_path, "wb") as tmpf:
                        tmpf.write(z.read(name))
                    text += f"\n--- {name} ---\n"
                    text += extract_text_from_pdf(tmp_path)
                elif name.endswith(".docx"):
                    tmp_path = f"/tmp/{os.path.basename(name)}"
                    with open(tmp_path, "wb") as tmpf:
                        tmpf.write(z.read(name))
                    text += f"\n--- {name} ---\n"
                    text += extract_text_from_docx(tmp_path)
                elif name.endswith(".txt"):
                    tmp_path = f"/tmp/{os.path.basename(name)}"
                    with open(tmp_path, "wb") as tmpf:
                        tmpf.write(z.read(name))
                    text += f"\n--- {name} ---\n"
                    text += extract_text_from_txt(tmp_path)
    except Exception as e:
        text += f"\n[ZIP READ ERROR: {file_path} | {e}]"
    return text

def load_documents(files):
    all_texts = {}
    for file_path in files:
        if file_path.endswith(".pdf"):
            all_texts[file_path] = extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            all_texts[file_path] = extract_text_from_docx(file_path)
        elif file_path.endswith(".txt"):
            all_texts[file_path] = extract_text_from_txt(file_path)
        elif file_path.endswith(".zip"):
            all_texts[file_path] = extract_text_from_zip(file_path)
        else:
            all_texts[file_path] = f"[Unsupported file type: {file_path}]"
    return all_texts

# -------------------------------
# Search Function
# -------------------------------
def search_documents(files, query):
    if not files or not query:
        return "No files uploaded or query is empty."
    
    docs_text = load_documents(files)
    results = []
    
    for file_name, content in docs_text.items():
        if query.lower() in content.lower():
            idx = content.lower().find(query.lower())
            start = max(idx - 50, 0)
            end = min(idx + 50, len(content))
            snippet = content[start:end].replace(query, f"**{query}**")
            results.append(f"📄 File: {os.path.basename(file_name)}\n\n🔎 Snippet: {snippet}\n")
        else:
            results.append(f"📄 File: {os.path.basename(file_name)}\n(no matches found)\n")
    
    return "\n\n---\n\n".join(results)

# -------------------------------
# Gradio App
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown(
        "<h1 style='text-align:center'>AI Document Search</h1>"
        "<p style='text-align:center'>Upload PDF, DOCX, TXT, or ZIP files and search them instantly.</p>"
    )
    
    with gr.Row():
        with gr.Column():
            upload_files = gr.File(
                file_types=[".pdf", ".docx", ".txt", ".zip"],
                file_types_count="multiple",   # ✅ correct way for multiple uploads
                label="Upload Documents"
            )
            query_input = gr.Textbox(label="Search Query", placeholder="Type a keyword or phrase...")
            search_btn = gr.Button("🔍 Search")
        
        with gr.Column():
            output_box = gr.Textbox(label="Search Results", lines=20)
    
    search_btn.click(
        search_documents,
        inputs=[upload_files, query_input],
        outputs=[output_box]
    )

demo.launch()
