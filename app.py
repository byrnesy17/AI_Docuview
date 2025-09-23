import gradio as gr
import fitz
from docx import Document
import zipfile, os, tempfile, shutil
import numpy as np
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# Initialize OpenAI client
client = OpenAI(api_key="YOUR_API_KEY")  # Replace with your key

def extract_text(file_path):
    """Extract text from PDF or DOCX with page/paragraph info."""
    text_data = []
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
    return text_data

def embed_texts(texts, batch_size=50):
    """Compute embeddings for a list of texts in batches for speed."""
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        embeddings.extend([np.array(e.embedding) for e in response.data])
    return embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def process_files(files):
    """Extract text and compute embeddings for all files (parallelized)."""
    temp_dir = tempfile.mkdtemp()
    all_text_data = []  # List of tuples: (file_name, location, text)

    def process_file(file_path):
        texts = []
        if file_path.lower().endswith(".zip"):
            extract_path = tempfile.mkdtemp(dir=temp_dir)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                for root, _, filenames in os.walk(extract_path):
                    for f in filenames:
                        if f.lower().endswith((".pdf", ".docx")):
                            texts.extend([(f, loc, line) for loc, line in extract_text(os.path.join(root, f))])
        else:
            texts.extend([(os.path.basename(file_path), loc, line) for loc, line in extract_text(file_path)])
        return texts

    # Parallel processing for speed
    with ThreadPoolExecutor() as executor:
        for result in executor.map(process_file, files):
            all_text_data.extend(result)

    # Separate text for embeddings
    text_only = [line for _, _, line in all_text_data]
    embeddings = embed_texts(text_only)
    # Store embeddings with corresponding metadata
    data_with_embeddings = []
    for (file_name, loc, text), emb in zip(all_text_data, embeddings):
        data_with_embeddings.append((file_name, loc, text, emb))

    return data_with_embeddings, temp_dir

def semantic_search(files, query):
    """Main function: processes files, computes embeddings, searches semantically."""
    data_with_embeddings, temp_dir = process_files(files)

    # Embed the query
    query_emb = embed_texts([query])[0]

    # Compute similarity for all lines
    results = []
    for file_name, loc, text, emb in data_with_embeddings:
        score = cosine_similarity(query_emb, emb)
        if score > 0.5:  # threshold for relevance
            results.append((score, file_name, loc, text))

    # Sort by relevance descending
    results.sort(reverse=True, key=lambda x: x[0])

    # Format output
    output = ""
    for score, file_name, loc, text in results[:100]:  # limit top 100 results
        output += f"[{score*100:.1f}%] {file_name} - {loc}: {text}\n\n"

    if output == "":
        output = "No relevant matches found."

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    return output

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# AI-Powered Document Search")
    with gr.Row():
        with gr.Column():
            file_input = gr.Files(label="Upload PDFs, Word Docs, or ZIPs", file_types=[".pdf",".docx",".zip"])
            query_input = gr.Textbox(label="Enter search query", placeholder="e.g., cars, engines, vehicles")
            search_btn = gr.Button("Search")
        with gr.Column():
            output = gr.Textbox(label="Results", lines=25)

    search_btn.click(semantic_search, inputs=[file_input, query_input], outputs=output)

demo.launch()
