import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
import nltk
import zipfile
import re
import math

nltk.download("wordnet")


# Read PDF
def read_pdf(file_path):
    pdf = PdfReader(file_path)
    text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


# Read DOCX
def read_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text


# Process uploaded files
def process_files(files):
    file_texts = {}
    summary_lines = []

    for file in files:
        ext = os.path.splitext(file)[1].lower()
        texts_to_add = []

        if ext == ".pdf":
            texts_to_add.append(read_pdf(file))
        elif ext == ".docx":
            texts_to_add.append(read_docx(file))
        elif ext == ".zip":
            with zipfile.ZipFile(file, "r") as zip_ref:
                for inner_file in zip_ref.namelist():
                    inner_ext = os.path.splitext(inner_file)[1].lower()
                    if inner_ext == ".pdf":
                        with zip_ref.open(inner_file) as f:
                            texts_to_add.append(read_pdf(f))
                    elif inner_ext == ".docx":
                        with zip_ref.open(inner_file) as f:
                            texts_to_add.append(read_docx(f))
                    else:
                        texts_to_add.append(f"Unsupported file type in ZIP: {inner_ext}")
        else:
            texts_to_add.append(f"Unsupported file type: {ext}")

        combined_text = "\n\n".join(texts_to_add)
        file_texts[file.name] = combined_text
        summary_lines.append(f"{file.name}: {len(combined_text)} characters")

    summary = "\n".join(summary_lines)
    return file_texts, summary


# Highlight matched terms
def highlight(text, term):
    if not term:
        return text
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)


# Paginate long text
def paginate_text(text, page, per_page=500):
    lines = text.split("\n")
    total_pages = math.ceil(len(lines) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_text = "\n".join(lines[start:end])
    return page_text, total_pages


# Generate HTML cards with pagination
def display_results_html(files, search_query="", page_num=1):
    file_texts, summary = process_files(files)
    html_content = ""

    for fname, text in file_texts.items():
        # Filter by search term
        filtered_lines = [line for line in text.split("\n") if search_query.lower() in line.lower()] \
            if search_query else text.split("\n")

        paginated_text, total_pages = paginate_text("\n".join(filtered_lines), page_num)

        highlighted_text = highlight(paginated_text, search_query)

        html_content += f"""
        <div style='border:1px solid #ccc; padding:10px; margin-bottom:10px; border-radius:8px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);'>
            <h3 style='margin:0; cursor:pointer; transition:color 0.3s;' 
                onclick="this.nextElementSibling.style.display = (this.nextElementSibling.style.display == 'none') ? 'block' : 'none';
                         this.style.color = (this.style.color=='#007BFF') ? 'black' : '#007BFF';">
                {fname} (Page {page_num}/{total_pages})
            </h3>
            <pre style='white-space: pre-wrap; padding-top:5px; max-height:400px; overflow:auto;'>{highlighted_text}</pre>
        </div>
        """

    return html_content, summary


# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## Document Reader & Advanced Search Tool (with Pagination)")
    gr.Markdown(
        "Upload PDF, DOCX, or ZIP files (ZIP can contain multiple PDFs/DOCXs). "
        "Click on file names to expand/collapse text. Matched search terms are highlighted."
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            file_types=[".pdf", ".docx", ".zip"],
            type="filepath",
            file_types_multiple=True
        )
        search_input = gr.Textbox(label="Search (real-time)", placeholder="Enter keyword")
        page_input = gr.Number(label="Page Number", value=1, precision=0)

    output_html = gr.HTML(label="Processed Texts")
    summary_box = gr.Textbox(label="Summary", lines=5, interactive=False)

    # Update results dynamically
    def update_results(files, query, page):
        if not files:
            return "", ""
        return display_results_html(files, query, page)

    inputs = [file_input, search_input, page_input]
    outputs = [output_html, summary_box]

    file_input.change(update_results, inputs, outputs)
    search_input.change(update_results, inputs, outputs)
    page_input.change(update_results, inputs, outputs)

demo.launch()
