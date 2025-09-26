import gradio as gr
from docx import Document
import PyPDF2

def process_file(file):
    """Simple demo of reading file content"""
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    elif file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        text = "\n".join([page.extract_text() for page in reader.pages])
        return text
    elif file.name.endswith(".docx"):
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text
    elif file.name.endswith(".zip"):
        return "ZIP file uploaded. Unzip and process files separately."
    else:
        return "Unsupported file type."

def search_documents(query, file_contents):
    """Simulate AI semantic search"""
    results = []
    for idx, content in enumerate(file_contents):
        if query.lower() in content.lower():
            results.append(f"File {idx+1} match:\n{content[:200]}...")
    return "\n\n".join(results) if results else "No matches found."

with gr.Blocks() as demo:
    gr.Markdown("## AI Document Search (Gradio Demo)")
    
    with gr.Row():
        uploaded_files = gr.File(file_types=[".pdf", ".docx", ".txt", ".zip"], file_types_multiple=True, label="Upload Documents")
    
    query = gr.Textbox(label="Search Query", placeholder="Enter keywords...")
    output = gr.Textbox(label="Search Results", interactive=False)
    
    def run_search(files, query_text):
        contents = [process_file(f) for f in files]
        return search_documents(query_text, contents)
    
    search_btn = gr.Button("Search")
    search_btn.click(run_search, inputs=[uploaded_files, query], outputs=output)

demo.launch()
