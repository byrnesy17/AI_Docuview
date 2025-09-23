import gradio as gr
import fitz
from docx import Document
import zipfile, os, tempfile, shutil
import numpy as np
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
import re

# --- Initialize model ---
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- Helper functions ---
def extract_text(file_path):
    """Extract text from PDF or DOCX"""
    text_data = []
    try:
        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                for line in page.get_text("text").split("\n"):
                    if line.strip():
                        text_data.append((f"Page {i+1}", i, line))  # include page index
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for idx, p in enumerate(doc.paragraphs, start=1):
                if p.text.strip():
                    text_data.append((f"Paragraph {idx}", None, p.text))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return text_data

def process_file(file_path, temp_dir):
    """Process PDF/DOCX or ZIP"""
    texts = []
    if file_path.lower().endswith(".zip"):
        extract_path = tempfile.mkdtemp(dir=temp_dir)
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            for root, _, filenames in os.walk(extract_path):
                for f in filenames:
                    if f.lower().endswith((".pdf", ".docx")):
                        texts.extend([(f, loc, line) for loc, page_idx, line in extract_text(os.path.join(root, f))])
        except Exception as e:
            print(f"Error extracting zip {file_path}: {e}")
    else:
        texts.extend([(os.path.basename(file_path), loc, line) for loc, page_idx, line in extract_text(file_path)])
    return texts

def compute_embeddings(lines, batch_size=50):
    embeddings = []
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i+batch_size]
        batch_emb = model.encode(batch, convert_to_numpy=True)
        embeddings.extend(batch_emb)
    return embeddings

def highlight_term_html(text, query):
    """Highlight search term in HTML"""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)

def get_pdf_image(file_path, page_index, sentence):
    """Render PDF page as image and highlight sentence"""
    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    draw = ImageDraw.Draw(img)
    # Simple highlight: find approximate rectangle of sentence
    text_instances = page.search_for(sentence, quads=True)
    for inst in text_instances:
        for quad in inst:
            x0, y0 = quad[:2]
            x1, y1 = quad[4:6]
            draw.rectangle([x0*2, y0*2, x1*2, y1*2], outline="red", width=3)

    return img

# --- Main generator function ---
def semantic_search_with_images(files, query):
    if not files:
        yield "Please upload files.", None, None
        return

    temp_dir = tempfile.mkdtemp()
    all_text_data = []

    # Step 1: Process files
    for idx, file in enumerate(files, start=1):
        yield f"Processing file {idx}/{len(files)}: {os.path.basename(file)}", None, None
        all_text_data.extend(process_file(file, temp_dir))

    if not all_text_data:
        shutil.rmtree(temp_dir, ignore_errors=True)
        yield "No readable content found.", None, None
        return

    # Step 2: Compute embeddings
    lines = [line for _, _, line in all_text_data]
    yield f"Computing embeddings for {len(lines)} lines...", None, None
    embeddings = compute_embeddings(lines)

    query_emb = model.encode([query], convert_to_numpy=True)[0]

    # Step 3: Compute similarity
    results = []
    first_match_images = []
    for (file_name, loc, line), emb in zip(all_text_data, embeddings):
        score = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb)))
        if score > 0.5:
            highlighted_line = highlight_term_html(line, query)
            results.append((score, file_name, loc, line, highlighted_line))
            # Yield live status for first match
            yield f"Found match in {file_name} - {loc}", highlighted_line, None

    # Sort top results
    results.sort(reverse=True, key=lambda x: x[0])
    top_results = results[:50]

    # Prepare DataFrame for display
    df = pd.DataFrame([
        {"File": f, "Location": loc, "Sentence": hl, "Similarity %": f"{score*100:.1f}%"}
        for score, f, loc, line, hl in top_results
    ])
    final_html = df.to_html(escape=False, index=False)

    # Step 4: Prepare first images for PDFs
    first_images = []
    for score, f, loc, line, hl in top_results:
        if f.lower().endswith(".pdf"):
            try:
                page_index = int(re.findall(r'\d+', loc)[0]) - 1
                img = get_pdf_image(f, page_index, line)
                first_images.append(img)
                # Only first match image per file
                break
            except:
                continue

    shutil.rmtree(temp_dir, ignore_errors=True)
    yield "✅ Search complete!", final_html, first_images[0] if first_images else None

# --- Gradio UI ---
with gr.Blocks() as demo:
    gr.Markdown("<h1 style='text-align:center'>🚀 AI-Powered Document Search & Visual Highlight</h1>")
    gr.Markdown("Upload PDFs, Word docs, or ZIP files. Enter a keyword or topic and see matches with semantic search, similarity scoring, highlighted sentences, and visual page snippets for PDFs.")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.Files(label="Upload PDFs / Word / ZIP", file_types=[".pdf",".docx",".zip"])
            query_input = gr.Textbox(label="Enter search query", placeholder="e.g., cars, engines, vehicles")
            search_btn = gr.Button("Search")
        with gr.Column(scale=2):
            status_box = gr.HTML(label="Status / Progress")
            output_box = gr.HTML(label="Results Table")
            image_box = gr.Image(label="PDF Page Preview (first match)", type="pil")

    search_btn.click(
        semantic_search_with_images,
        inputs=[file_input, query_input],
        outputs=[status_box, output_box, image_box]
    )

demo.launch()
