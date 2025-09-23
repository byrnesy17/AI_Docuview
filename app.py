import gradio as gr
import fitz  # PyMuPDF
from docx import Document
import zipfile
import os
import tempfile

def extract_text_with_pages(file_path):
    text_data = []
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            for line in page.get_text("text").split("\n"):
                if line.strip():
                    text_data.append((i+1, line))
    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                text_data.append((None, p.text))
    return text_data

def search_documents(files, keyword):
    results = ""
    temp_dir = tempfile.mkdtemp()
    all_files = []

    # Ensure files is always a list
    if not isinstance(files, list):
        files = [files]

    for file in files:
        # If zip, extract contents
        if file.lower().endswith(".zip"):
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                for root, _, filenames in os.walk(temp_dir):
                    for f in filenames:
                        if f.lower().endswith((".pdf", ".docx")):
                            all_files.append(os.path.join(root, f))
        else:
            all_files.append(file)

    # Search for keyword
    for file_path in all_files:
        text_data = extract_text_with_pages(file_path)
        matches = []
        for page_num, line in text_data:
            if keyword.lower() in line.lower():
                if page_num:
                    matches.append(f"(Page {page_num}) {line}")
                else:
                    matches.append(line)
        if matches:
            results += f"--- {os.path.basename(file_path)} ---\n"
            results += "\n".join(matches) + "\n\n"

    if results == "":
        results = "No matches found."
    return results

demo = gr.Interface(
    fn=search_documents,
    inputs=[
        gr.Files(  # ✅ Changed from gr.File to gr.Files for multiple uploads
            label="Upload PDFs, Word files, or zip folders",
            type="filepath",
            file_types=[".pdf", ".docx", ".zip"]
        ),
        gr.Textbox(label="Keyword to search")
    ],
    outputs=gr.Textbox(label="Search Results", lines=20),
    title="Document Keyword Search",
    description="Upload PDFs, Word documents, or zip folders and search for keywords across all files. PDF matches show page numbers."
)

demo.launch()
