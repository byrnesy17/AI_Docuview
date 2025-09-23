import gradio as gr
import fitz
from docx import Document
import zipfile, os, tempfile, shutil, io, base64, re
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

def get_pdf_image_base64(file_path, page_index, sentence):
    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    try:
        text_instances = page.search_for(sentence)
        for inst in text_instances:
            x0, y0, x1, y1 = inst[:4]
            draw.rectangle([x0*2, y0*2, x1*2, y1*2], outline="red", width=3)
    except:
        pass
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# -------------------------------
# Build interactive table with live filter
# -------------------------------
def build_interactive_table(top_results, pdf_images):
    table_html = """
    <input type="text" id="searchBox" placeholder="Filter by keyword, file, similarity %" 
        style="width: 100%; padding:5px; margin-bottom:10px; font-size:16px;">
    <table id="resultsTable" border='1' style='border-collapse:collapse;width:100%;'>
    <tr><th>Keyword</th><th>File</th><th>Location</th><th>Sentence</th><th>Similarity %</th></tr>
    """

    for score, kw, f, loc, line, hl in top_results:
        row_id = re.sub(r'\W','', f"{f}_{loc}_{score*100:.1f}")
        imgs_html = "".join([f'<img src="data:image/png;base64,{b64img}" style="max-width:400px;margin:5px;">' 
                             for b64img in pdf_images.get(f, [])])
        table_html += f"""
        <tr onclick="document.getElementById('{row_id}').style.display =
        document.getElementById('{row_id}').style.display=='none'?'table-row':'none';"
        style="cursor:pointer;background-color:rgba({int(255*(1-score))},{int(255*score)},0,0.3)">
        <td>{kw}</td><td>{f}</td><td>{loc}</td><td>{hl}</td><td>{score*100:.1f}%</td></tr>
        <tr id="{row_id}" style="display:none;"><td colspan='5'>{imgs_html}<br><b>Full Sentence:</b> {line}</td></tr>
        """
    table_html += "</table>"

    # JS for live filtering
    table_html += """
    <script>
    const searchBox = document.getElementById('searchBox');
    searchBox.addEventListener('input', function(){
        const filter = searchBox.value.toLowerCase();
        const table = document.getElementById('resultsTable');
        const trs = table.getElementsByTagName('tr');
        for (let i = 1; i < trs.length; i+=2) {
            const tds = trs[i].getElementsByTagName('td');
            const text = Array.from(tds).map(td=>td.innerText.toLowerCase()).join(" ");
            trs[i].style.display = text.includes(filter) ? '' : 'none';
            const detailRow = trs[i+1];
            if(detailRow) detailRow.style.display = 'none';
        }
    });
    </script>
    """
    return table_html

# -------------------------------
# Semantic Search
# -------------------------------
def semantic_search(files, query_str, similarity_threshold=0.5):
    if not files:
        return {"status":"Please upload files.","progress":0}, None, None

    keywords = [k.strip() for k in query_str.split(",") if k.strip()]
    if not keywords:
        return {"status":"Please enter valid keywords.","progress":0}, None, None

    temp_dir = tempfile.mkdtemp()
    all_text_data = []

    for idx, file in enumerate(files, start=1):
        all_text_data.extend(process_file(file, temp_dir))

    if not all_text_data:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"status":"No readable content found.","progress":100}, None, None

    lines = [line for _, _, line in all_text_data]
    embeddings = compute_embeddings(lines)
    keyword_embeddings = model.encode(keywords, convert_to_numpy=True)

    results = []
    pdf_images = {}

    for ((file_name, loc, line), emb) in zip(all_text_data, embeddings):
        for kw, kw_emb in zip(keywords, keyword_embeddings):
            score = float(np.dot(kw_emb, emb)/(np.linalg.norm(kw_emb)*np.linalg.norm(emb)))
            if score >= similarity_threshold:
                highlighted_line = highlight_terms_html(line, [kw])
                results.append((score, kw, file_name, loc, line, highlighted_line))
                if file_name.lower().endswith(".pdf"):
                    page_index = int(re.findall(r'\d+', loc)[0])-1
                    if file_name not in pdf_images:
                        pdf_images[file_name] = []
                    pdf_images[file_name].append(get_pdf_image_base64(file_name, page_index, line))

    results.sort(reverse=True, key=lambda x: x[0])
    top_results = results[:100]

    table_html = build_interactive_table(top_results, pdf_images)

    summary_html = pd.DataFrame([{"File":f, 
                                  "Total Matches":len([r for r in top_results if r[2]==f]), 
                                  "Average Similarity %":f"{np.mean([r[0] for r in top_results if r[2]==f])*100:.1f}%",
                                  "Top Sentences":"<br>".join([r[5] for r in top_results if r[2]==f][:5])} 
                                  for f in set(r[2] for r in top_results)]
                               ).to_html(escape=False, index=False)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return {"status": "Search complete.","progress":100}, table_html, summary_html

# -------------------------------
# Gradio Interface
# -------------------------------
with gr.Blocks(title="Advanced Document Keyword & Semantic Search") as demo:
    gr.Markdown("### Upload multiple PDFs, Word documents, or ZIPs and search with intelligent semantic matching.")
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(file_types=[".pdf",".docx",".zip"], file_types_multiple=True, label="Upload Documents")
            keyword_input = gr.Textbox(label="Keywords (comma-separated)")
            search_btn = gr.Button("Search")
            progress_info = gr.Label(value="Status: Waiting for input...")
            progress_bar = gr.Progress()
        with gr.Column(scale=2):
            result_html = gr.HTML(label="Results Table")
            summary_html = gr.HTML(label="Summary")

    search_btn.click(semantic_search, 
                     inputs=[file_input, keyword_input], 
                     outputs=[progress_info, result_html, summary_html])

demo.launch()
