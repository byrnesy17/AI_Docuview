import gradio as gr
from PyPDF2 import PdfReader
import docx
import zipfile
import os
import nltk

# Download NLTK wordnet data if missing
import nltk
from nltk.corpus import wordnet
try:
    wordnet.synsets("test")
except:
    nltk.download("wordnet")

# ------------------------------
# File Reading Functions
# ------------------------------
def read_pdf(file_path):
    try:
        pdf = PdfReader(file_path)
        text = ""
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"[PDF READ ERROR: {file_path} | {e}]"

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[DOCX READ ERROR: {file_path} | {e}]"

def read_zip(file_path):
    text = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                if name.endswith(".pdf"):
                    with zip_ref.open(name) as f:
                        temp_path = f"/tmp/{os.path.basename(name)}"
                        with open(temp_path, "wb") as tmp:
                            tmp.write(f.read())
                        text.append(read_pdf(temp_path))
                elif name.endswith(".docx"):
                    with zip_ref.open(name) as f:
                        temp_path = f"/tmp/{os.path.basename(name)}"
                        with open(temp_path, "wb") as tmp:
                            tmp.write(f.read())
                        text.append(read_docx(temp_path))
                else:
                    text.append(f"[Unsupported file inside ZIP: {name}]")
        return "\n\n---\n\n".join(text)
    except Exception as e:
        return f"[ZIP READ ERROR: {file_path} | {e}]"

# ------------------------------
# Processing & Searching
# ------------------------------
def process_files(files):
    if not files:
        return "[No files uploaded]"
    all_texts = []
    for file_path in files:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(file_path))
        elif ext == ".docx":
            all_texts.append(read_docx(file_path))
        elif ext == ".zip":
            all_texts.append(read_zip(file_path))
        else:
            all_texts.append(f"[Unsupported file type: {ext}]")
    return "\n\n---\n\n".join(all_texts)

def search_in_text(files, query):
    if not files or not query:
        return "[No files uploaded or search query is empty]"
    try:
        full_text = process_files(files)
    except Exception as e:
        return f"[Error processing files: {str(e)}]"

    lines = full_text.split("\n")
    results = [line for line in lines if query.lower() in line.lower()]
    if not results:
        return "[No matches found]"
    return "\n".join(results)

# ------------------------------
# Gradio UI
# ------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📄 Document Reader & Search Tool")
    gr.Markdown(
        """
        Upload PDF, DOCX, or ZIP files (containing PDFs/DOCXs).  
        Extract text or search for specific keywords in your documents.
        """
    )

    with gr.Tab("Extract Text"):
        file_input = gr.File(
            label="Upload Documents",
            file_count="multiple",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath"
        )
        output_text = gr.Textbox(label="Extracted Text", lines=20)
        submit_btn = gr.Button("Process Files")
        submit_btn.click(process_files, inputs=file_input, outputs=output_text)

    with gr.Tab("Search Text"):
        search_files = gr.File(
            label="Upload Documents",
            file_count="multiple",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath"
        )
        search_query = gr.Textbox(label="Search Query")
        search_output = gr.Textbox(label="Search Results", lines=20)
        search_btn = gr.Button("Search")
        search_btn.click(search_in_text, inputs=[search_files, search_query], outputs=search_output)

demo.launch()
