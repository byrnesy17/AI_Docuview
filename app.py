import os
import gradio as gr
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
from docx import Document
from fuzzywuzzy import fuzz

# Load semantic search model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to extract text from uploaded files
def extract_text(file):
    ext = os.path.splitext(file.name)[1].lower()
    text = ""
    if ext == ".pdf":
        reader = PdfReader(file.name)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif ext == ".docx":
        doc = Document(file.name)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

# Process uploaded zip or single files
def process_files(files, query):
    results = []
    for file in files:
        text = extract_text(file)
        # Semantic similarity
        sentences = [s.strip() for s in text.split("\n") if s.strip()]
        embeddings = model.encode(sentences)
        query_embedding = model.encode([query])[0]

        for i, sent in enumerate(sentences):
            sim_score = float(model.similarity(query_embedding, embeddings[i]))
            fuzzy_score = fuzz.partial_ratio(query.lower(), sent.lower())
            if sim_score > 0.5 or fuzzy_score > 70:  # adjustable thresholds
                results.append({
                    "file": file.name,
                    "sentence": sent,
                    "similarity": round(sim_score, 2),
                    "fuzzy": fuzzy_score
                })
    # Sort results by highest similarity
    results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    return results

# Generate HTML card-style for Gradio
def format_results(results):
    html = "<div style='display:flex; flex-wrap:wrap; gap:15px;'>"
    for r in results:
        html += f"""
        <div style='border:1px solid #ccc; border-radius:12px; padding:15px; width:300px; box-shadow:2px 2px 12px rgba(0,0,0,0.1);'>
            <h4>{r['file']}</h4>
            <p>{r['sentence']}</p>
            <p><b>Similarity:</b> {r['similarity']} | <b>Fuzzy:</b> {r['fuzzy']}</p>
            <button onclick="alert('File: {r['file']}\\nSentence: {r['sentence']}')">View</button>
        </div>
        """
    html += "</div>"
    return html

# Gradio Interface
with gr.Blocks(css="""
    .gr-button {background-color:#4CAF50;color:white;font-weight:bold;}
    .gr-file {border:2px dashed #4CAF50;}
""") as demo:

    gr.Markdown("# 📄 AI Document Search")
    query_input = gr.Textbox(label="Search Query", placeholder="Type something like 'animal', 'cow', etc.", lines=1)
    file_input = gr.File(label="Upload PDFs or Word Documents", type="file", file_types=[".pdf", ".docx"], file_types_multiple=True)
    result_html = gr.HTML()

    search_btn = gr.Button("Search 🔍")
    search_btn.click(
        lambda files, q: format_results(process_files(files, q)),
        inputs=[file_input, query_input],
        outputs=result_html
    )

demo.launch()
