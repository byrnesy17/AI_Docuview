import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import zipfile
import shutil
import nltk
from nltk.corpus import wordnet

# Ensure NLTK wordnet data is downloaded
nltk.download("wordnet")

# -------------------
# File Reading Functions
# -------------------

def read_pdf(file_path):
    """Extract text from PDF"""
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def read_docx(file_path):
    """Extract text from DOCX"""
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def read_zip(file_path):
    """Extract supported files from ZIP and return combined text"""
    texts = []
    temp_dir = "temp_zip"
    os.makedirs(temp_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)
        for fname in zip_ref.namelist():
            fpath = os.path.join(temp_dir, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext == ".pdf":
                texts.append(read_pdf(fpath))
            elif ext == ".docx":
                texts.append(read_docx(fpath))
            else:
                texts.append(f"Unsupported file in ZIP: {fname}")
    shutil.rmtree(temp_dir)
    return "\n\n---\n\n".join(texts)

# -------------------
# Process Uploaded Files
# -------------------

def process_files(file_paths):
    all_texts = []
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(path))
        elif ext == ".docx":
            all_texts.append(read_docx(path))
        elif ext == ".zip":
            all_texts.append(read_zip(path))
        else:
            all_texts.append(f"Unsupported file type: {ext}")
    combined_text = "\n\n---\n\n".join(all_texts)
    return combined_text

# -------------------
# Search Function
# -------------------

def search_text(extracted_text, query):
    if not extracted_text.strip():
        return "No text extracted yet. Please process files first."
    if not query.strip():
        return "Please enter a search term."
    lines = extracted_text.splitlines()
    results = [line for line in lines if query.lower() in line.lower()]
    return "\n".join(results) if results else "No results found."

# -------------------
# Gradio Interface
# -------------------

with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Search Tool")
    gr.Markdown(
        "Upload PDF, DOCX, or ZIP files containing these formats. "
        "Extract text and search across all documents."
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents (PDF, DOCX, ZIP)",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath",
            file_types_multiple=False  # Gradio v5 handles multiple files automatically
        )

    output_text = gr.Textbox(label="Extracted Text", lines=20)

    query_input = gr.Textbox(label="Search Text", placeholder="Enter search term here")
    search_output = gr.Textbox(label="Search Results", lines=10)

    with gr.Row():
        process_btn = gr.Button("Process Files")
        search_btn = gr.Button("Search Text")

    process_btn.click(fn=process_files, inputs=file_input, outputs=output_text)
    search_btn.click(fn=search_text, inputs=[output_text, query_input], outputs=search_output)

# Launch the app
demo.launch()
