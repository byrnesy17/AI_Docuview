import gradio as gr
from PyPDF2 import PdfReader
from docx import Document
import zipfile
import io
from sentence_transformers import SentenceTransformer, util
import os
import tempfile

# Load AI model for semantic search
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text(file_bytes, filename):
    """Extract text from PDF or DOCX"""
    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    elif filename.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

def search_documents(zip_file, query):
    """Search for query across all documents in uploaded ZIP"""
    results = []
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_file.name, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    query_embedding = model.encode(query, convert_to_tensor=True)

    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith((".pdf", ".docx")):
                path = os.path.join(root, file)
                with open(path, "rb") as f:
                    text = extract_text(f.read(), file)
                    if not text.strip():
                        continue
                    # Semantic search
                    sentences = [s.strip() for s in text.split("\n") if s.strip()]
                    embeddings = model.encode(sentences, convert_to_tensor=True)
                    scores = util.cos_sim(query_embedding, embeddings)[0]
                    top_results = [(sentences[i], float(scores[i])) for i in range(len(sentences)) if scores[i] > 0.5]
                    if top_results:
                        results.append({
                            "file": file,
                            "matches": sorted(top_results, key=lambda x: x[1], reverse=True)
                        })

    # Create card-style output
    output_components = []
    for r in results:
        matches_text = "\n\n".join([f"**{match[0]}** (score: {match[1]:.2f})" for match in r["matches"][:5]])
        card = gr.Card(r["file"], matches_text)
        output_components.append(card)

    if not output_components:
        return "No matches found."
    return output_components

with gr.Blocks() as demo:
    gr.Markdown("## AI-Powered Meeting Minutes Search")
    with gr.Row():
        zip_input = gr.File(label="Upload ZIP of PDFs/DOCs", file_types=[".zip"])
        query_input = gr.Textbox(label="Search Query", placeholder="Enter word, phrase, or concept")
    search_btn = gr.Button("Search")
    output_area = gr.Column()
    
    search_btn.click(search_documents, inputs=[zip_input, query_input], outputs=[output_area])

demo.launch()
