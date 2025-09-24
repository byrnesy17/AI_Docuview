import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import zipfile
import nltk
from nltk.corpus import wordnet

# Download NLTK wordnet
nltk.download("wordnet")

# ------------------------------
# File reading functions
# ------------------------------
def read_pdf(file_path):
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def read_zip(file_path):
    text = ""
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        for file_info in zip_ref.infolist():
            name = file_info.filename
            ext = os.path.splitext(name)[1].lower()
            if ext == ".pdf":
                zip_ref.extract(file_info, "/tmp")
                text += read_pdf(os.path.join("/tmp", name)) + "\n\n---\n\n"
            elif ext == ".docx":
                zip_ref.extract(file_info, "/tmp")
                text += read_docx(os.path.join("/tmp", name)) + "\n\n---\n\n"
            else:
                text += f"Unsupported file type in zip: {ext}\n\n---\n\n"
    return text

# ------------------------------
# Process uploaded files
# ------------------------------
def process_files(files):
    all_texts = []
    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(file.name))
        elif ext == ".docx":
            all_texts.append(read_docx(file.name))
        elif ext == ".zip":
            all_texts.append(read_zip(file.name))
        else:
            all_texts.append(f"Unsupported file type: {ext}")
    return "\n\n---\n\n".join(all_texts)

# ------------------------------
# Search function
# ------------------------------
def search_in_text(files, query):
    full_text = process_files(files)
    lines = full_text.split("\n")
    results = [line for line in lines if query.lower() in line.lower()]
    if not results:
        return "No matches found."
    return "\n".join(results)

# ------------------------------
# Gradio UI
# ------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Search")
    gr.Markdown("Upload PDF, DOCX, or ZIP files, then extract text or search for keywords.")

    file_input = gr.File(
        label="Upload Documents",
        file_types=[".pdf", ".docx", ".zip"],
        type="filepath"  # Correct argument
    )

    search_query = gr.Textbox(label="Search Query", placeholder="Enter text to search for...", lines=1)
    extracted_text = gr.Textbox(label="Extracted Text", lines=20, interactive=False)

    with gr.Row():
        process_btn = gr.Button("Extract Text")
        search_btn = gr.Button("Search in Files")

    process_btn.click(process_files, inputs=file_input, outputs=extracted_text)
    search_btn.click(search_in_text, inputs=[file_input, search_query], outputs=extracted_text)

demo.launch()
