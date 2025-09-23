import gradio as gr
import fitz  # PyMuPDF
from docx import Document
import zipfile
import os
import tempfile
import shutil

def extract_text_with_pages(file_path):
    """Extracts text from PDF or Word document and returns list of (location, text)."""
    text_data = []
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            for line in page.get_text("text").split("\n"):
                if line.strip():
                    text_data.append((f"Page {i+1}", line))
    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for idx, p in enumerate(doc.paragraphs, start=1):
            if p.text.strip():
                text_data.append((f"Paragraph {idx}", p.text))
    return text_data

def search_documents(files, keyword):
    """Search for keyword in uploaded files (PDF, DOCX, ZIP)."""
    results = ""
    temp_dir = tempfile.mkdtemp()
    all_files = []

    # Ensure files is always a list
    if not isinstance(files, list):
        files = [files]

    # Extract files and collect all PDFs/DOCs
    for file in files:
        if file.lower().endswith(".zip"):
            with zipfile.ZipFile(file, 'r') as zip_ref:
                extract_path = tempfile.mkdtemp(dir=temp_dir)
                zip_ref.extractall(extract_path)
                for root, _, filenames in os.walk(extract_path):
                    for f in filenames:
                        if f.lower().endswith((".pdf", ".docx")):
                            all_files.append(os.path.join(root, f))
        else:
            all_files.append(file)

    # Search keyword in all files
    for file_path in all_files:
        text_data = extract_text_with_pages(file_path)
        matches = []
        for location, line in text_data:
            if keyword.lower() in line.lower():
                # Optional: highlight keyword in line
                highlighted = line.replace(keyword, f"**{keyword}**")
                matches.append(f"{location}: {highlighted}")

        if matches:
            results += f"--- {os.path.basename(file_path)} ---\n"
            results += "\n".join(matches) + "\n\n"

    if results == "":
        results = "No matches found."

    # Clean up temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)
    return results

demo = gr.Interface(
    fn=search_documents,
    inputs=[
        gr.Files(
            label="Upload PDFs, Word files, or zip folders",
            type="filepath",
            file_types=[".pdf", ".docx", ".zip"]
        ),
        gr.Textbox(label="Keyword to search")
    ],
    outputs=gr.Textbox(label="Search Results", lines=25),
    title="Document Keyword Search",
    description="Upload PDFs, Word documents, or zip folders and search for keywords across all files. PDF matches show page numbers, Word matches show paragraph numbers."
)

demo.launch()
