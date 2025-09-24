import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import zipfile
import nltk
from nltk.corpus import wordnet

# Ensure NLTK wordnet data is downloaded
nltk.download("wordnet")

# Read PDF files
def read_pdf(file_path):
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# Read DOCX files
def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

# Process ZIP files
def read_zip(file_path):
    texts = {}
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall("/tmp/zip_extract")
        for f in zip_ref.namelist():
            ext = os.path.splitext(f)[1].lower()
            full_path = os.path.join("/tmp/zip_extract", f)
            if ext == ".pdf":
                texts[f] = read_pdf(full_path)
            elif ext == ".docx":
                texts[f] = read_docx(full_path)
            else:
                texts[f] = f"Unsupported file in ZIP: {f}"
    return texts

# Process files with optional search
def process_files(files, search_query=""):
    file_texts = {}
    summary = []
    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        if ext == ".pdf":
            file_texts[file.name] = read_pdf(file.name)
        elif ext == ".docx":
            file_texts[file.name] = read_docx(file.name)
        elif ext == ".zip":
            zip_texts = read_zip(file.name)
            file_texts.update(zip_texts)
        else:
            file_texts[file.name] = f"Unsupported file type: {ext}"

    # Apply search
    if search_query.strip():
        for fname in file_texts:
            lines = file_texts[fname].splitlines()
            matches = [line for line in lines if search_query.lower() in line.lower()]
            file_texts[fname] = "\n".join(matches) if matches else "No results found."

    # Build summary
    for fname, text in file_texts.items():
        paragraphs = len([p for p in text.splitlines() if p.strip()])
        pages = text.count("\f") + 1  # crude page count for PDFs
        summary.append(f"{fname} — Pages: {pages}, Paragraphs: {paragraphs}")

    return file_texts, "\n".join(summary)

# UI
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Search Tool")
    gr.Markdown(
        "Upload PDF, DOCX, or ZIP files. ZIP files can contain multiple PDFs/DOCXs. "
        "Optionally, search for a keyword to filter results. Each document is shown in its own card."
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath",
        )
        search_input = gr.Textbox(label="Search (optional)", placeholder="Enter keyword")

    output_container = gr.Accordion(label="Processed Documents", open=True)
    summary_box = gr.Textbox(label="Summary", lines=5, interactive=False)

    submit_btn = gr.Button("Process Files")

    def display_results(files, search_query):
        file_texts, summary = process_files(files, search_query)
        accordion_items = []
        for fname, text in file_texts.items():
            accordion_items.append(gr.Markdown(f"### {fname}\n\n{text}"))
        return accordion_items, summary

    submit_btn.click(
        fn=display_results,
        inputs=[file_input, search_input],
        outputs=[output_container, summary_box]
    )

demo.launch()
