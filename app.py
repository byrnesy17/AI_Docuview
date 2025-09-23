import gradio as gr
import fitz
from docx import Document
import zipfile, os, tempfile, re, hashlib, asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from nltk.corpus import wordnet
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# -----------------------------
# Initialize semantic model
# -----------------------------
model = SentenceTransformer('all-MiniLM-L6-v2')

# -----------------------------
# Caching
# -----------------------------
highlight_cache = {}
precomputed_embeddings = {}

# -----------------------------
# Helper Functions
# -----------------------------
def expand_keywords(keywords):
    expanded = set()
    for kw in keywords:
        expanded.add(kw)
        for syn in wordnet.synsets(kw):
            for lemma in syn.lemmas():
                expanded.add(lemma.name().replace("_"," "))
    return list(expanded)

def extract_text_chunks(file_path, chunk_size=500):
    """Splits text into smaller chunks for faster embeddings."""
    text_data = []
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page_text = page.get_text("text").strip()
            if page_text:
                lines = page_text.split("\n")
                chunk = ""
                for line in lines:
                    if len(chunk) + len(line) < chunk_size:
                        chunk += line + " "
                    else:
                        text_data.append((file_path, f"Page {i+1}", i, chunk.strip()))
                        chunk = line + " "
                if chunk.strip():
                    text_data.append((file_path, f"Page {i+1}", i, chunk.strip()))
    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for idx, p in enumerate(doc.paragraphs, start=1):
            text = p.text.strip()
            if text:
                text_data.append((file_path, f"Paragraph {idx}", None, text))
    return text_data

def assign_colors(keywords):
    import random
    random.seed(42)
    colors = ["#FFB6C1","#87CEFA","#90EE90","#FFA500","#DA70D6","#FFFF00","#00CED1","#FF6347"]
    return {kw: colors[i % len(colors)] for i, kw in enumerate(keywords)}

def highlight_terms_html(text, keywords):
    color_map = assign_colors(keywords)
    def repl(m):
        kw = m.group(0)
        return f"<mark style='background-color:{color_map.get(kw.lower(), 'yellow')}'>{kw}</mark>"
    pattern = re.compile("|".join(re.escape(k.strip()) for k in keywords), re.IGNORECASE)
    return pattern.sub(repl, text)

# -----------------------------
# Async Preprocessing with Embeddings
# -----------------------------
async def preprocess_file_async(file_path, temp_dir, chunk_size=500):
    all_text_data = []
    # Handle ZIP extraction
    files_to_process = []
    if file_path.lower().endswith(".zip"):
        extract_path = tempfile.mkdtemp(dir=temp_dir)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
        for root, _, files in os.walk(extract_path):
            for f in files:
                if f.lower().endswith((".pdf",".docx")):
                    files_to_process.append(os.path.join(root, f))
    else:
        files_to_process.append(file_path)

    for f in files_to_process:
        chunks = extract_text_chunks(f, chunk_size)
        all_text_data.extend(chunks)
        # Precompute embeddings
        texts = [c[3] for c in chunks]
        if texts:
            precomputed_embeddings[f] = model.encode(texts, convert_to_numpy=True)
    return all_text_data

async def preprocess_files_async(files, progress=gr.Progress()):
    temp_dir = tempfile.mkdtemp()
    total = len(files)
    all_text_data = []

    for idx, file in enumerate(files):
        progress((idx+1)/total, f"Processing {os.path.basename(file)} ({idx+1}/{total})")
        chunks = await preprocess_file_async(file, temp_dir)
        all_text_data.extend(chunks)
    return all_text_data

# -----------------------------
# Semantic Search using Vectorized NumPy
# -----------------------------
def semantic_search_vector(query, all_text_data, threshold=0.5):
    if not query.strip() or not all_text_data:
        return []

    base_keywords = [k.strip() for k in query.split(",") if k.strip()]
    keywords = expand_keywords(base_keywords)
    keyword_embeddings = model.encode(keywords, convert_to_numpy=True)

    results = []
    for idx, (file_path, location, page_index, text) in enumerate(all_text_data):
        text_embs = precomputed_embeddings.get(file_path)
        if text_embs is None:
            continue
        for i, emb in enumerate(text_embs):
            sims = np.dot(keyword_embeddings, emb)/(np.linalg.norm(keyword_embeddings, axis=1)*np.linalg.norm(emb))
            max_score = float(np.max(sims))
            if max_score >= threshold:
                highlighted = highlight_terms_html(text, keywords)
                results.append({
                    "file": file_path,
                    "location": location,
                    "page_index": page_index if page_index is not None else 0,
                    "sentence": highlighted,
                    "score": max_score,
                    "keywords": keywords,
                    "type": os.path.splitext(file_path)[1].lower()
                })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# -----------------------------
# Gradio UI (simplified for clarity)
# -----------------------------
with gr.Blocks(title="Ultra Fast Document Explorer") as demo:
    gr.Markdown("### Upload multiple documents (PDF, Word, ZIP). Semantic search with highlighted results and fast performance.")
    
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="Upload Documents", file_types=[".pdf",".docx",".zip"], file_types="multiple")
            keyword_input = gr.Textbox(label="Keywords (comma separated)")
            threshold_input = gr.Slider(label="Min Similarity", minimum=0, maximum=1, step=0.01, value=0.5)
            export_btn = gr.File(label="Export CSV")
        with gr.Column(scale=2):
            sentence_display = gr.HTML(label="Highlighted Sentence")
            results_table = gr.Dataframe(headers=["File","Location","Score"], datatype=["str","str","number"], interactive=True)
    
    all_text_data_store = gr.State()
    search_results_store = gr.State()
    selected_index = gr.State(0)

    # -----------------------------
    # File Upload Preprocessing
    # -----------------------------
    file_input.upload(fn=preprocess_files_async, inputs=file_input, outputs=[all_text_data_store])

    # -----------------------------
    # Semantic Search Trigger
    # -----------------------------
    def search_documents(query, all_text_data, threshold):
        results = semantic_search_vector(query, all_text_data, threshold)
        table_data = [[r['file'], r['location'], round(r['score'],2)] for r in results]
        return table_data, results, 0

    keyword_input.change(search_documents,
                         inputs=[keyword_input, all_text_data_store, threshold_input],
                         outputs=[results_table, search_results_store, selected_index])

    # -----------------------------
    # Show highlighted sentence on row select
    # -----------------------------
    def update_preview(index, results):
        if not results or index < 0 or index >= len(results):
            return ""
        r = results[index]
        return r['sentence']

    results_table.select(update_preview, inputs=[selected_index, search_results_store], outputs=[sentence_display])

    # -----------------------------
    # Export CSV
    # -----------------------------
    def export_results_csv(results):
        if not results: return None
        import csv, tempfile, re
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        with open(temp_file.name, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["File","Location","Sentence","Score"])
            for r in results:
                writer.writerow([r['file'], r['location'], re.sub("<[^>]+>", "", r['sentence']), f"{r['score']:.2f}"])
        return temp_file.name

    export_btn.click(export_results_csv, inputs=[search_results_store], outputs=[export_btn])

demo.launch()
