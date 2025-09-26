import gradio as gr
import os
import zipfile
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer, util
import rapidfuzz

# Load AI model
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- File extraction functions ---
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_zip(file):
    texts = {}
    with zipfile.ZipFile(file, 'r') as z:
        for filename in z.namelist():
            if filename.endswith('.pdf'):
                with z.open(filename) as f:
                    texts[filename] = extract_text_from_pdf(f)
            elif filename.endswith('.docx'):
                with z.open(filename) as f:
                    texts[filename] = extract_text_from_docx(f)
    return texts

def load_files(files):
    all_texts = {}
    for file in files:
        name = os.path.basename(file.name)
        if name.endswith('.pdf'):
            all_texts[name] = extract_text_from_pdf(file.name)
        elif name.endswith('.docx'):
            all_texts[name] = extract_text_from_docx(file.name)
        elif name.endswith('.zip'):
            all_texts.update(extract_text_from_zip(file.name))
    return all_texts

# --- Search function ---
def search_documents(files, query):
    all_texts = load_files(files)
    query_embedding = model.encode(query, convert_to_tensor=True)
    results = []

    for fname, text in all_texts.items():
        sentences = [s.strip() for s in text.split('\n') if s.strip()]
        if not sentences:
            continue
        sentence_embeddings = model.encode(sentences, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, sentence_embeddings)[0]

        # Top 5 matches
        top_results = sorted(
            [(sentences[i], float(cosine_scores[i])) for i in range(len(sentences))],
            key=lambda x: x[1], reverse=True
        )[:5]

        for sent, score in top_results:
            ratio = rapidfuzz.fuzz.partial_ratio(query.lower(), sent.lower())
            # Highlight exact matches
            highlighted = sent.replace(query, f"**{query}**")
            results.append({
                "Document": fname,
                "Sentence": highlighted,
                "Score": round(score, 3),
                "Similarity": ratio
            })

    # Convert to card-style list for Gradio
    cards = []
    for r in results:
        cards.append(gr.Markdown(f"**Document:** {r['Document']}\n\n**Score:** {r['Score']}, **Similarity:** {r['Similarity']}\n\n{r['Sentence']}"))

    return cards if cards else ["No matches found."]

# --- Gradio UI ---
with gr.Blocks() as demo:
    gr.Markdown("# AI-Powered Document Search")
    gr.Markdown("Upload PDFs, Word docs, or ZIPs. Search for words or similar sentences. Results are shown as cards with highlights.")

    with gr.Row():
        file_input = gr.File(label="Upload Documents", file_types=[".pdf", ".docx", ".zip"], type="file", file_types_count="multiple")
        query_input = gr.Textbox(label="Search Query", placeholder="Enter word or phrase")

    search_btn = gr.Button("Search")
    output = gr.Column()

    search_btn.click(fn=search_documents, inputs=[file_input, query_input], outputs=[output])

demo.launch()
