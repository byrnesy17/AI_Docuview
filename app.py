import gradio as gr
import os
import zipfile
from PyPDF2 import PdfReader
import docx
import nltk
from nltk.corpus import wordnet

# Ensure NLTK wordnet data is downloaded
nltk.download("wordnet")

# -------------------------------
# File Reading Functions
# -------------------------------
def read_pdf(file_path):
    try:
        pdf = PdfReader(file_path)
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"Error reading DOCX: {e}"

def read_zip(file_path):
    texts = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall("/tmp/zip_extract")
            for f in zip_ref.namelist():
                extracted_path = os.path.join("/tmp/zip_extract", f)
                ext = os.path.splitext(extracted_path)[1].lower()
                if ext == ".pdf":
                    texts.append(read_pdf(extracted_path))
                elif ext == ".docx":
                    texts.append(read_docx(extracted_path))
                else:
                    texts.append(f"Unsupported file in ZIP: {f}")
        return "\n\n---\n\n".join(texts)
    except Exception as e:
        return f"Error reading ZIP: {e}"

# -------------------------------
# Process Uploaded Files
# -------------------------------
def process_files(file_paths, search_query):
    if not file_paths:
        return "No files uploaded."

    if not isinstance(file_paths, list):
        file_paths = [file_paths]

    all_texts = []
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            all_texts.append(read_pdf(path))
        elif ext == ".docx":
            all_texts.append(read_docx(path))
        elif ext == ".zip":
            all_texts.append(read_zip(path))
        else:
            all_texts.append(f"Unsupported file type: {ext}")

    combined_text = "\n\n---\n\n".join(all_texts)

    # Search functionality
    if search_query:
        lines = combined_text.split("\n")
        results = [line for line in lines if search_query.lower() in line.lower()]
        if results:
            return "\n".join(results)
        else:
            return f"No results found for: '{search_query}'"

    return combined_text

# -------------------------------
# Gradio Interface
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## Professional Document Reader & Search Tool")

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents (PDF, DOCX, ZIP)",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath"  # Required for multiple files
        )
        search_input = gr.Textbox(
            label="Search Query (optional)",
            placeholder="Enter text to search across documents..."
        )

    output_text = gr.Textbox(
        label="Extracted Text / Search Results",
        lines=25
    )

    submit_btn = gr.Button("Process & Search")
    submit_btn.click(
        fn=process_files,
        inputs=[file_input, search_input],
        outputs=output_text
    )

demo.launch()
