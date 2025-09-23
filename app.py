import gradio as gr
import fitz
from docx import Document
import zipfile, os, tempfile, shutil, io, re
import numpy as np
from PIL import Image, ImageDraw
import pandas as pd
from sentence_transformers import SentenceTransformer

# -------------------------------
# Initialize model
# -------------------------------
model = SentenceTransformer('all-MiniLM-L6-v2')

# -------------------------------
# Helper Functions
# -------------------------------
def extract_text(file_path):
    text_data = []
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            for line in page.get_text("text").split("\n"):
                if line.strip():
                    text_data.append((f"Page {i+1}", i, line))
    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for idx, p in enumerate(doc.paragraphs, start=1):
            if p.text.strip():
                text_data.append((f"Paragraph {idx}", None, p.text))
    return text_data

def process_file(file_path, temp_dir):
    texts = []
    if file_path.lower().endswith(".zip"):
        extract_path = tempfile.mkdtemp(dir=temp_dir)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
        for root, _, filenames in os.walk(extract_path):
            for f in filenames:
                if f.lower().endswith((".pdf", ".docx")):
                    texts.extend([(f, loc, line) for loc, page_idx, line in extract_text(os.path.join(root, f))])
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

def highlight_terms_html(text, keywords):
    pattern = re.compile("|".join(re.escape(k.strip()) for k in keywords), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark style='background-color:yellow'>{m.group(0)}</mark>", text)

def get_pdf_image(file_path, page_index, sentence):
    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    try:
        text_instances = page.search_for(sentence, quads=True)
        for inst in text_instances:
            for quad in inst:
                x0, y0 = quad[:2]
                x1, y1 = quad[4:6]
                draw.rectangle([x0*2, y0*2, x1*2, y1*2], outline="red", width=3)
    except:
        pass
    return img

# -------------------------------
# Semantic Search Generator
# -------------------------------
def semantic_search(files, query_str, similarity_threshold=0.5):
    if not files: 
        yield "❌ Upload some files to search.", None, None, None, None
        return
    keywords = [k.strip() for k in query_str.split(",") if k.strip()]
    if not keywords:
        yield "❌ Enter valid keywords.", None, None, None, None
        return

    temp_dir = tempfile.mkdtemp()
    all_text_data = []

    # -------------------------------
    # Processing files
    # -------------------------------
    for idx, file in enumerate(files, start=1):
        yield f"🔹 Processing file {idx}/{len(files)}: {os.path.basename(file)}", None, None, None, None
        all_text_data.extend(process_file(file, temp_dir))

    if not all_text_data:
        shutil.rmtree(temp_dir, ignore_errors=True)
        yield "❌ No readable content found.", None, None, None, None
        return

    lines = [line for _, _, line in all_text_data]
    yield f"⚡ Computing embeddings for {len(lines)} lines...", None, None, None, None
    embeddings = compute_embeddings(lines)
    keyword_embeddings = model.encode(keywords, convert_to_numpy=True)

    results = []
    pdf_match_images = {}
    pdf_match_pages = {}

    for (file_name, loc, line), emb in zip(all_text_data, embeddings):
        for kw, kw_emb in zip(keywords, keyword_embeddings):
            score = float(np.dot(kw_emb, emb)/(np.linalg.norm(kw_emb)*np.linalg.norm(emb)))
            if score >= similarity_threshold:
                highlighted_line = highlight_terms_html(line, [kw])
                results.append((score, kw, file_name, loc, line, highlighted_line))
                if file_name.lower().endswith(".pdf"):
                    page_index = int(re.findall(r'\d+', loc)[0])-1
                    if file_name not in pdf_match_images:
                        pdf_match_images[file_name] = []
                        pdf_match_pages[file_name] = []
                    pdf_match_images[file_name].append(get_pdf_image(file_name, page_index, line))
                    pdf_match_pages[file_name].append(page_index)
                yield f"✅ Found '{kw}' in {file_name} - {loc}", highlighted_line, None, None, None

    results.sort(reverse=True, key=lambda x: x[0])
    top_results = results[:100]

    # Color-coded table
    df = pd.DataFrame([
        {"Keyword": kw, "File": f, "Location": loc, "Sentence": hl, "Similarity %": f"{score*100:.1f}%"}
        for score, kw, f, loc, line, hl in top_results
    ])
    final_html = df.to_html(escape=False, index=False)

    summary_data = []
    for f in set(f for _, _, f, _, _, _ in top_results):
        file_matches = [r for r in top_results if r[2]==f]
        avg_score = np.mean([r[0] for r in file_matches])
        summary_data.append({
            "File": f,
            "Total Matches": len(file_matches),
            "Average Similarity %": f"{avg_score*100:.1f}%",
            "Top Sentences": "<br>".join([r[5] for r in file_matches[:5]])
        })
    summary_df = pd.DataFrame(summary_data)
    summary_html = summary_df.to_html(escape=False, index=False)

    shutil.rmtree(temp_dir, ignore_errors=True)
    yield "🎯 Search complete!", final_html, summary_html, top_results, (pdf_match_images, pdf_match_pages)

# -------------------------------
# Export functions
# -------------------------------
def export_results_csv(all_results):
    if all_results is None:
        return None
    df = pd.DataFrame([
        {"Keyword": kw, "File": f, "Location": loc, "Sentence": line, "Similarity %": f"{score*100:.1f}%"}
        for score, kw, f, loc, line, hl in all_results
    ])
    temp_file = tempfile.mktemp(suffix=".csv")
    df.to_csv(temp_file, index=False)
    return temp_file

def export_pdf_snippets(all_results, pdf_states):
    if all_results is None or pdf_states is None:
        return None
    pdf_match_images, _ = pdf_states
    if not pdf_match_images:
        return None
    zip_path = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_name, images in pdf_match_images.items():
            for idx, img in enumerate(images, start=1):
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                zipf.writestr(f"{os.path.basename(file_name)}_match_{idx}.png", img_bytes.read())
    return zip_path

# -------------------------------
# Preview navigation
# -------------------------------
def update_preview(selected_index, all_results, pdf_states):
    if selected_index is None or all_results is None:
        return "", None, 0
    score, kw, file_name, loc, line, highlighted_line = all_results[selected_index]
    pdf_match_images, _ = pdf_states if pdf_states else ({}, {})
    images = pdf_match_images.get(file_name, [])
    return highlighted_line, images[0] if images else None, 0

def next_pdf(current_index, file_name, pdf_states):
    pdf_match_images, _ = pdf_states if pdf_states else ({}, {})
    images = pdf_match_images.get(file_name, [])
    if not images:
        return None, 0
    next_index = (current_index + 1) % len(images)
    return images[next_index], next_index

def prev_pdf(current_index, file_name, pdf_states):
    pdf_match_images, _ = pdf_states if pdf_states else ({}, {})
    images = pdf_match_images.get(file_name, [])
    if not images:
        return None, 0
    prev_index = (current_index - 1) % len(images)
    return images[prev_index], prev_index

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks(css="""
body {background-color:#f7f9fc; font-family:Arial,sans-serif;}
h1 {color:#0d6efd;}
mark {background-color: #ffff66;}
""") as demo:
    gr.Markdown("<h1 style='text-align:center'>🚀 Enterprise AI Document Search</h1>")
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.Files(label="Upload PDFs / Word / ZIP", file_types=[".pdf",".docx",".zip"])
            query_input = gr.Textbox(label="Enter keywords (comma-separated)", placeholder="e.g., cars, engines, vehicles")
            similarity_slider = gr.Slider(0.0,1.0,value=0.5,label="Similarity Threshold")
            search_btn = gr.Button("Search", elem_id="search-btn")
            export_csv_btn = gr.Button("Export Results CSV")
            export_csv_file = gr.File(label="Download CSV")
            export_pdf_btn = gr.Button("Export PDF Snippets ZIP")
            export_pdf_file = gr.File(label="Download PDF Snippets ZIP")
        with gr.Column(scale=2):
            status_box = gr.HTML(label="Status / Progress")
            tabs = gr.Tabs()
            with tabs:
                with gr.Tab("Results Table"):
                    output_box = gr.DataFrame(headers=["Keyword","File","Location","Sentence","Similarity %"], interactive=True)
                with gr.Tab("File Summary"):
                    summary_box = gr.HTML(label="File Summary")
                with gr.Tab("Preview"):
                    preview_text = gr.HTML(label="Full Sentence Preview")
                    preview_image = gr.Image(label="PDF Page Preview", type="pil")
                    prev_btn = gr.Button("⬅ Previous Match")
                    next_btn = gr.Button("Next Match ➡")
                    pdf_index_state = gr.State(0)
                    selected_index_state = gr.State(None)

    results_state = gr.State()
    pdf_states = gr.State()

    search_btn.click(
        semantic_search,
        inputs=[file_input, query_input, similarity_slider],
        outputs=[status_box, output_box, summary_box, results_state, pdf_states]
    )

    export_csv_btn.click(
        fn=export_results_csv,
        inputs=[results_state],
        outputs=[export_csv_file]
    )

    export_pdf_btn.click(
        fn=export_pdf_snippets,
        inputs=[results_state, pdf_states],
        outputs=[export_pdf_file]
    )

    def table_select_callback(df_row):
        index = df_row.name
        return update_preview(index, results_state.value, pdf_states.value)

    output_box.select(
        table_select_callback,
        inputs=[],
        outputs=[preview_text, preview_image, pdf_index_state]
    )

    prev_btn.click(
        prev_pdf,
        inputs=[pdf_index_state, selected_index_state, pdf_states],
        outputs=[preview_image, pdf_index_state]
    )
    next_btn.click(
        next_pdf,
        inputs=[pdf_index_state, selected_index_state, pdf_states],
        outputs=[preview_image, pdf_index_state]
    )

demo.launch()
