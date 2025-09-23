import gradio as gr
import fitz  # PyMuPDF
from docx import Document
import zipfile
import os
import tempfile

def extract_text(file_path):
    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text
    else:
        return ""

def search_documents(files, keyword):
    results = ""
    temp_dir = tempfile.mkdtemp()

    all_files = []

    # Extract files if zip, otherwise add directly
    for file in files:
        if file.name.endswith(".zip"):
            with zipfile.ZipFile(file.name, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                for root, _, filenames in os.walk(temp_dir):
                    for f in filenames:
                        if f.lower().endswith((".pdf", ".docx")):
                            all_files.append(os.path.join(root, f))
        else:
            all_files.append(file.name)

    # Search for keyword in all files
    for file_path in all_files:
        text = extract_text(file_path)
        matches = [line for line in text.split("\n") if keyword.lower() in line.lower()]
        if matches:
            results += f"--- {os.path.basename(file_path)} ---\n"
            results += "\n".join(matches) + "\n\n"

    if results == "":
        results = "No matches found."
    return results

demo = gr.Interface(
    fn=search_documents,
    inputs=[
        gr.File(file_types=[".pdf", ".docx", ".zip"], label="Upload PDFs, Word files, or zip folders", file_types_multiple=True),
        gr.Textbox(label="Keyword to search")
    ],
    outputs=gr.Textbox(label="Search Results", lines=20),
    title="Document Keyword Search",
    description="Upload multiple PDFs, Word documents, or zip folders conta
