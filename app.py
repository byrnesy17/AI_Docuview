import gradio as gr
import os
import zipfile
from PyPDF2 import PdfReader
import docx
import nltk

# Download NLTK data
nltk.download("wordnet")

# ---------------------------
# File reading functions
# ---------------------------
def read_pdf(file_path):
    try:
        pdf = PdfReader(file_path)
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {e}"

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text.strip()
    except Exception as e:
        return f"Error reading DOCX: {e}"

# ---------------------------
# Highlight search term
# ---------------------------
def highlight_term(text, term):
    if not term:
        return text
    import re
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)

# ---------------------------
# Process uploaded files
# ---------------------------
def process_files(files, search_term=None):
    if not files:
        return "", "No files uploaded."

    file_cards = ""
    extracted_texts = []

    all_files_to_process = []

    # Handle zip files
    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        if ext == ".zip":
            try:
                with zipfile.ZipFile(file.name, 'r') as zip_ref:
                    for zip_file in zip_ref.namelist():
                        zip_ext = os.path.splitext(zip_file)[1].lower()
                        if zip_ext in [".pdf", ".docx"]:
                            zip_ref.extract(zip_file, "/tmp")
                            all_files_to_process.append(os.path.join("/tmp", zip_file))
                        else:
                            file_cards += f"- {zip_file} : Unsupported inside zip\n"
                file_cards += f"- {file.name} : ZIP processed\n"
            except Exception as e:
                file_cards += f"- {file.name} : Failed to extract zip ({e})\n"
        else:
            all_files_to_process.append(file.name)

    # Process PDFs and DOCX
    for file_path in all_files_to_process:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            text = read_pdf(file_path)
            status = "Processed"
        elif ext == ".docx":
            text = read_docx(file_path)
            status = "Processed"
        else:
            text = f"Unsupported file type: {ext}"
            status = "Unsupported"

        file_cards += f"- {os.path.basename(file_path)} : {status}\n"

        if search_term and ext in [".pdf", ".docx"]:
            text = highlight_term(text, search_term)

        extracted_texts.append(f"### {os.path.basename(file_path)}\n{text}\n\n---\n\n")

    return file_cards, "".join(extracted_texts)

# ---------------------------
# Gradio UI
# ---------------------------
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Search Tool")
    gr.Markdown(
        "Upload PDF, DOCX, or ZIP files. ZIPs will be extracted automatically. "
        "Search across all files with term highlighting. Professional, clean interface."
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath",
            file_types_allow_multiple=True
        )
        search_input = gr.Textbox(
            label="Search Term (optional)",
            placeholder="Enter a term to search across all files..."
        )

    output_cards = gr.Textbox(
        label="File Upload Status",
        lines=8,
        interactive=False
    )

    output_text = gr.Markdown(
        label="Extracted Text & Search Results",
        interactive=False
    )

    submit_btn = gr.Button("Process Files")
    submit_btn.click(
        process_files,
        inputs=[file_input, search_input],
        outputs=[output_cards, output_text]
    )

demo.launch()
