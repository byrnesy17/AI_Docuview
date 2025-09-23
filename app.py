import gradio as gr
import fitz  # PyMuPDF
from docx import Document
import zipfile, os, tempfile, shutil
import numpy as np
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor

# Initialize local embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text(file_path):
    """Extract text from PDF or DOCX with location info."""
    text_data = []
    try:
        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                for line in page.get_text("text").split("\n"):
                    if line.strip():
                        text_data.append((f"Page {i+1}", line))
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for idx, p in enumerate(doc.paragraphs, start=1):
                if p.text.strip():
                    text_data.append((f"Paragraph {idx}", p.text))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return text_data

def process_file(file_path, temp_dir):
    """Process single file or zip."""
    texts = []
    if file_path.lower().endswith(".zip"):
        extract_path = tempfile.mkdtemp(dir=temp_dir)
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            for root, _, filenames in os.walk(extract_path):
                for f in filenames:
                    if f.lower().endswith((".pdf", ".docx")):
                        texts.extend([(f, loc, line) 
                                      for loc, line in extract_text(os.path.join(root, f))])
        except Exception as e:
            print(f"Error extracting zip {file_path}: {e}")
    else:
        texts.extend([(os.path.basename(file_path), loc, line) 
                      for loc, line in extract_text(file_path)])
    return texts

def compute_embeddings(lines, batch_size=50):
    """Compute embeddings in batches for speed."""
    embeddings = []
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i+batch_size]
        batch_emb = model.encode(batch, convert_to_numpy=True)
        embeddings.extend(batch_emb)
    return embeddings

def semantic_search(files, query):
    if not files:
        return "Please upload at least one file."

    temp_dir = tempfile.mkdtemp()
    all_text_data = []

    # Parallel file processing
    with ThreadPoolExecutor() as executor:
        for result in executor.map(lambda f: process_file(f, temp_dir), files):
            all_text_data.extend(result)

    if not all_text_data:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return "No readable content found in uploaded files."

    # Compute embeddings
    lines = [line for _, _, line in all_text_data]
    embeddings = compute_embeddings(lines)

    # Embed query
    query_emb = model.encode([query], convert_to_numpy=True)[0]

    # Compute similarity
    results = []
    for (file_name, loc, line), emb in zip(all_text_data, embeddings):
        score = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb)))
        if score > 0.5:  # threshold
            highlighted = line.replace(query, f"**{query}**")
            results.append((score, file_name, loc, highlighted))

    # Sort by similarity descending
    results.sort(reverse=True, key=lambda x: x[0])

    output = ""
    for score, file_name, loc, line in results[:100]:  # top 100 results
        output += f"[{score*100:.1f}%] {file_name} - {loc}: {line}\n\n"

    if not output:
        output = "No relevant matches found."

    shutil.rmtree(temp_dir, ignore_errors=True)
    return output

# --- Gradio UI ---
with gr.Blocks() as demo:
    gr.Markdown("<h1 style='text-align:center'>📄 AI-Powered Meeting Minutes Search</h1>")
    gr.Markdown("Upload multiple PDFs, Word docs, or ZIP files. Enter a search query to find relevant topics and related terms across all documents.")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.Files(label="Upload PDFs / Word / ZIP", file_types=[".pdf",".docx",".zip"])
            query_input = gr.Textbox(label="Enter search query", placeholder="e.g., cars, engines, vehicles")
            search_btn = gr.Button("Search")
        with gr.Column(scale=2):
            output_box = gr.Textbox(label="Search Results", lines=25, interactive=False)

    search_btn.click(semantic_search, inputs=[file_input, query_input], outputs=output_box)

demo.launch()
