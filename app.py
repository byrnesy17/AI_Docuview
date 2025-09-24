import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import nltk
from nltk.corpus import wordnet

# Download NLTK wordnet data
nltk.download("wordnet")

# Function to read PDF files
def read_pdf(file_path):
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text

# Function to read DOCX files
def read_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text

# Function to process uploaded files
def process_files(files):
    all_texts = []
    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(file.name))
        elif ext == ".docx":
            all_texts.append(read_docx(file.name))
        else:
            all_texts.append(f"Unsupported file type: {ext}")
    return "\n\n---\n\n".join(all_texts)

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader")

    # Allow multiple file uploads
    file_input = gr.File(
        label="Upload Documents",
        file_types=[".pdf", ".docx"],
        type="file",
        file_types_multiple=True  # Correct property for multiple files
    )

    output_text = gr.Textbox(label="Extracted Text", lines=20)

    submit_btn = gr.Button("Process Files")
    submit_btn.click(process_files, inputs=file_input, outputs=output_text)

demo.launch()
