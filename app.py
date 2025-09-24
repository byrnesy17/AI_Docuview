import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import zipfile
import nltk
from nltk.corpus import wordnet

# Ensure NLTK wordnet data is downloaded
nltk.download("wordnet")

# --- File reading functions ---
def read_pdf(file_path):
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text

def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def read_zip(file_path):
    texts = []
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall("temp_zip")
        for fname in zip_ref.namelist():
            fpath = os.path.join("temp_zip", fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext == ".pdf":
                texts.append(read_pdf(fpath))
            elif ext == ".docx":
                texts.append(read_docx(fpath))
            else:
                texts.append(f"Unsupported file in ZIP: {fname}")
    return "\n\n---\n\n".join(texts)

# --- Process uploaded files ---
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

# --- Search function ---
def search_text(extracted_text, query):
    if not query.strip():
        return "Please enter a search term."
    lines = extracted_text.splitlines()
    results = [line for line in lines if query.lower() in line.lower()]
    return "\n".join(results) if results else "No results found."

# --- Gradio UI ---
with gr.Blocks() as demo:
    gr.Markdown("## Professional Document Reader & Search Tool")

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents (PDF, DOCX, ZIP)",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath"  # Correct way to handle multiple files in Gradio v5+
        )
    
    output_text = gr.Textbox(label="Extracted Text", lines=20)
    
    submit_btn = gr.Button("Process Files")
    submit_btn.click(process_files, inputs=file_input, outputs=output_text)

    gr.Markdown("### Search in Extracted Text")
    search_input = gr.Textbox(label="Enter search term", placeholder="Type a word or phrase to search...")
    search_btn = gr.Button("Search")
    search_output = gr.Textbox(label="Search Results", lines=15)
    
    search_btn.click(search_text, inputs=[output_text, search_input], outputs=search_output)

demo.launch()
