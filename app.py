import gradio as gr
import os
import zipfile
from io import BytesIO
from PyPDF2 import PdfReader
import docx
from sentence_transformers import SentenceTransformer, util

# Load AI model for semantic search
model = SentenceTransformer('all-MiniLM-L6-v2')

# In-memory storage of uploaded docs
documents = {}

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def upload_files(files):
    """
    Accept multiple files (PDF, DOCX, or ZIP) and extract text.
    """
    documents.clear()
    for file in files:
        file_name = os.path.basename(file.name)
        if file_name.endswith(".zip"):
            # Extract ZIP contents
            with zipfile.ZipFile(file.name, 'r') as zip_ref:
                for inner_file in zip_ref.namelist():
                    ext = os.path.splitext(inner_file)[1].lower()
                    if ext in [".pdf", ".docx"]:
                        data = zip_ref.read(inner_file)
                        temp_path = f"/tmp/{inner_file}"
                        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                        with open(temp_path, "wb") as f:
                            f.write(data)
                        if ext == ".pdf":
                            documents[inner_file] = extract_text_from_pdf(temp_path)
                        else:
                            documents[inner_file] = extract_text_from_docx(temp_path)
        else:
            ext = os.path.splitext(file_name)[1].lower()
            if ext == ".pdf":
                documents[file_name] = extract_text_from_pdf(file.name)
            elif ext == ".docx":
                documents[file_name] = extract_text_from_docx(file.name)
    return f"Uploaded {len(documents)} documents successfully!"

def search_documents(query):
    """
    Search uploaded documents using semantic similarity.
    """
    results = []
    query_emb = model.encode(query, convert_to_tensor=True)
    
    for doc_name, content in documents.items():
        sentences = content.split("\n")
        embeddings = model.encode(sentences, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_emb, embeddings)[0]
        
        # Get top 3 matching sentences
        top_results = cosine_scores.topk(k=min(3, len(sentences)))
        for score, idx in zip(top_results.values, top_results.indices):
            snippet = sentences[idx]
            highlighted = snippet.replace(query, f"<mark>{query}</mark>")
            results.append({
                "document": doc_name,
                "snippet": highlighted,
                "score": float(score)
            })
    
    # Sort by score descending
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    if not results:
        return "<p>No matches found.</p>"
    
    # Generate HTML cards
    html = ""
    for r in results:
        html += f"""
        <div class='card'>
            <h3>{r['document']}</h3>
            <p>{r['snippet']}</p>
        </div>
        """
    return html

# Custom CSS for card style
css = """
<style>
.card {
    background: #f7f9fc;
    border-radius: 12px;
    padding: 16px;
    margin: 10px 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: transform 0.2s;
}
.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}
mark {
    background-color: #fffa65;
}
</style>
"""

with gr.Blocks() as demo:
    gr.HTML("<h1>📄 AI Document & Meeting Minutes Search</h1>")
    gr.HTML("<p>Upload PDF/DOCX/ZIP files, enter a search query, and see results highlighted in interactive cards.</p>")
    file_input = gr.File(label="Upload Documents (PDF, DOCX, ZIP)", file_types=[".pdf", ".docx", ".zip"], file_types_count="multiple")
    upload_btn = gr.Button("Upload Files")
    search_input = gr.Textbox(label="Search Query")
    search_btn = gr.Button("Search")
    output_html = gr.HTML()
    
    upload_btn.click(upload_files, inputs=file_input, outputs=output_html)
    search_btn.click(search_documents, inputs=search_input, outputs=output_html)
    gr.HTML(css)

demo.launch()
