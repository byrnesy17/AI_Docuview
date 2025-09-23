import gradio as gr
from sentence_transformers import SentenceTransformer, util
from PyPDF2 import PdfReader
from docx import Document
from io import BytesIO
import re
import pandas as pd

# Load small model from Hugging Face hub (fast & lightweight)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Extract text from PDF in-memory
def extract_pdf_text(file_bytes):
    pdf = PdfReader(BytesIO(file_bytes))
    texts = []
    for page in pdf.pages:
        texts.append(page.extract_text())
    return "\n".join(texts)

# Extract text from DOCX in-memory
def extract_docx_text(file_bytes):
    doc = Document(BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

# Search text in all uploaded files
def search_documents(files, query):
    results = []
    for uploaded_file in files:
        name = uploaded_file.name
        content = None
        if name.lower().endswith(".pdf"):
            content = extract_pdf_text(uploaded_file.read())
        elif name.lower().endswith(".docx"):
            content = extract_docx_text(uploaded_file.read())
        else:
            continue

        # Split into sentences
        sentences = re.split(r'(?<=[.!?]) +', content)
        for sentence in sentences:
            if query.lower() in sentence.lower():
                # Highlight the match
                highlighted = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", sentence, flags=re.IGNORECASE)
                results.append({
                    "file": name,
                    "sentence": highlighted
                })

    df = pd.DataFrame(results)
    return df.to_dict(orient="records")

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## Document Search Tool")
    
    with gr.Row():
        file_input = gr.File(label="Upload Documents", file_types=[".pdf", ".docx"], file_types_multiple=True)
        search_input = gr.Textbox(label="Search Query", placeholder="Enter word or phrase...")
        search_button = gr.Button("Search")
    
    result_table = gr.Dataframe(headers=["File", "Sentence"], interactive=False)

    search_button.click(
        search_documents,
        inputs=[file_input, search_input],
        outputs=result_table
    )

demo.launch()
