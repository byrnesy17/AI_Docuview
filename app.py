import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import nltk
from nltk.corpus import wordnet

# Ensure NLTK WordNet data is downloaded
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

# Function to process uploaded files (accepts a list of files)
def process_files(files):
    if not files:
        return "No files uploaded."
    
    all_texts = []
    for file in files:
        # Hugging Face uploads files as temp paths
        file_path = file.name
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(file_path))
        elif ext == ".docx":
            all_texts.append(read_docx(file_path))
        else:
            all_texts.append(f"Unsupported file type: {ext}")
    return "\n\n---\n\n".join(all_texts)

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader")
    
    # ✅ Multi-file upload works without 'file_types_multiple'
    file_input = gr.File(label="Upload Documents", file_types=[".pdf", ".docx"], type="file", file_types_multiple=False, file_types_multiple=True)

    output_text = gr.Textbox(label="Extracted Text", lines=20)

    submit_btn = gr.Button("Process Files")
    submit_btn.click(process_files, inputs=file_input, outputs=output_text)

demo.launch()
