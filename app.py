import gradio as gr
import os
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import nltk

nltk.download('wordnet')

# Function to extract text from PDFs
def extract_text_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# Function to extract text from DOCX
def extract_text_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text

# Main search function
def search_documents(files, keyword):
    results = []
    for file_obj in files:
        file_name = os.path.basename(file_obj.name)
        ext = os.path.splitext(file_name)[1].lower()
        text = ""
        if ext == ".pdf":
            text = extract_text_pdf(file_obj.name)
        elif ext == ".docx":
            text = extract_text_docx(file_obj.name)
        else:
            continue

        # find sentences containing the keyword
        sentences = [s for s in text.split("\n") if keyword.lower() in s.lower()]
        for s in sentences:
            results.append({"File": file_name, "Sentence": s})

    df = pd.DataFrame(results)
    return df

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## Document Search App\nUpload PDF or DOCX files and search for keywords.")
    
    file_input = gr.File(label="Upload Documents", file_types=[".pdf", ".docx"], file_types_multiple=True)
    keyword_input = gr.Textbox(label="Keyword")
    search_btn = gr.Button("Search")
    output_table = gr.Dataframe(headers=["File", "Sentence"], datatype=["str", "str"])
    
    search_btn.click(fn=search_documents, inputs=[file_input, keyword_input], outputs=output_table)

demo.launch()
