import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import zipfile
import nltk
from nltk.corpus import wordnet

nltk.download("wordnet")

# --- File Reading Functions ---
def read_pdf(file_path):
    try:
        pdf = PdfReader(file_path)
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF {file_path}: {str(e)}"

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"Error reading DOCX {file_path}: {str(e)}"

def read_zip(file_path):
    extracted_texts = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall("temp_zip")
            for filename in zip_ref.namelist():
                ext = os.path.splitext(filename)[1].lower()
                full_path = os.path.join("temp_zip", filename)
                if ext == ".pdf":
                    extracted_texts.append((filename, read_pdf(full_path)))
                elif ext == ".docx":
                    extracted_texts.append((filename, read_docx(full_path)))
                else:
                    extracted_texts.append((filename, f"Unsupported file in zip: {filename}"))
        return extracted_texts
    except Exception as e:
        return [("ZIP Error", f"Error reading ZIP {file_path}: {str(e)}")]

# --- Process Uploaded Files & Dashboard ---
def process_files(files, search_term=""):
    tab_texts = []
    stats = {"Total Files": len(files), "PDF":0, "DOCX":0, "ZIP":0, "Unsupported":0, "Word Counts":{}}

    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        if ext == ".pdf":
            content = read_pdf(file.name)
            stats["PDF"] += 1
        elif ext == ".docx":
            content = read_docx(file.name)
            stats["DOCX"] += 1
        elif ext == ".zip":
            zip_contents = read_zip(file.name)
            stats["ZIP"] += 1
            tab_texts.extend(zip_contents)
            continue
        else:
            content = f"Unsupported file type: {ext}"
            stats["Unsupported"] += 1

        tab_texts.append((file.name, content))

    # Highlight search term
    if search_term.strip():
        highlighted_tabs = []
        for fname, text in tab_texts:
            highlighted_text = text.replace(search_term, f"**{search_term}**")
            highlighted_tabs.append((fname, highlighted_text))
        tab_texts = highlighted_tabs

    # Word counts
    for fname, text in tab_texts:
        stats["Word Counts"][fname] = len(text.split())

    return stats, {fname: text for fname, text in tab_texts}

# --- Gradio Interface ---
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Dashboard")
    gr.Markdown(
        "Upload PDF, DOCX, or ZIP files. You can upload multiple files at once. "
        "Use the search box to highlight keywords in each document."
    )

    file_input = gr.File(
        label="Upload Documents",
        file_types=[".pdf", ".docx", ".zip"],
        file_types_allow_multiple=True,
        type="filepath"
    )

    search_input = gr.Textbox(
        label="Search Term (Optional)",
        placeholder="Enter a word or phrase to highlight..."
    )

    dashboard = gr.Markdown(label="Dashboard")
    output_tabs = gr.TabbedInterface([], label="Documents")

    submit_btn = gr.Button("Process Files")
    submit_btn.click(
        fn=process_files,
        inputs=[file_input, search_input],
        outputs=[dashboard, output_tabs]
    )

demo.launch()
