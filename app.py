import gradio as gr
import os
import zipfile
import tempfile
import shutil
import nltk
from nltk.corpus import wordnet
from PyPDF2 import PdfReader
import docx
from sentence_transformers import SentenceTransformer, util

# Make sure WordNet is downloaded
nltk.download("wordnet", quiet=True)

# Load semantic search model
model = SentenceTransformer("all-MiniLM-L6-v2")

# ========== File Processing Helpers ==========
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text += f"\n[Error reading PDF: {e}]"
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text += f"\n[Error reading DOCX: {e}]"
    return text

def preprocess_files(files):
    all_texts = {}
    temp_dir = tempfile.mkdtemp()

    try:
        for file in files:
            filename = os.path.basename(file.name)
            file_path = os.path.join(temp_dir, filename)
            shutil.copy(file.name, file_path)

            # Handle zip archives
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                for root, _, inner_files in os.walk(temp_dir):
                    for inner_file in inner_files:
                        if inner_file.endswith(".pdf"):
                            all_texts[inner_file] = extract_text_from_pdf(os.path.join(root, inner_file))
                        elif inner_file.endswith(".docx"):
                            all_texts[inner_file] = extract_text_from_docx(os.path.join(root, inner_file))
            else:
                if filename.endswith(".pdf"):
                    all_texts[filename] = extract_text_from_pdf(file_path)
                elif filename.endswith(".docx"):
                    all_texts[filename] = extract_text_from_docx(file_path)
    finally:
        shutil.rmtree(temp_dir)

    return all_texts

# Expand search query with synonyms
def expand_query(query):
    synonyms = set()
    for syn in wordnet.synsets(query):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))
    return list(synonyms)[:5]  # Limit synonyms for efficiency

# Main search function
def semantic_search(files, query):
    if not files:
        return "Please upload at least one file.", None, None

    all_texts = preprocess_files(files)
    results = []

    query_variants = [query] + expand_query(query)
    query_embeddings = model.encode(query_variants, convert_to_tensor=True)

    for filename, text in all_texts.items():
        sentences = text.split("\n")
        sentence_embeddings = model.encode(sentences, convert_to_tensor=True)

        cos_scores = util.cos_sim(query_embeddings, sentence_embeddings).max(0)
        top_results = cos_scores.topk(3)

        for score, idx in zip(top_results[0], top_results[1]):
            if score.item() > 0.3:  # Filter weak matches
                results.append({
                    "file": filename,
                    "sentence": sentences[idx],
                    "score": round(score.item() * 100, 2)
                })

    if not results:
        return "No relevant matches found.", None, None

    # Sort by score
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # Display results
    table_output = "### Search Results\n| File | Relevance | Sentence |\n|------|-----------|----------|\n"
    for r in results:
        table_output += f"| {r['file']} | {r['score']}% | {r['sentence']} |\n"

    # List of sentences for UI selection
    sentences_list = [f"{r['file']} → {r['sentence']} ({r['score']}%)" for r in results]

    return table_output, sentences_list, results

# ========== Gradio UI ==========
with gr.Blocks(css=".gradio-container {max-width: 900px !important}") as demo:
    gr.Markdown("# Document Search Tool\nUpload PDFs, DOCX, or ZIP archives and search with AI-powered semantic matching.")

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            type="file",
            file_types=[".pdf", ".docx", ".zip"]
        )
        query_input = gr.Textbox(label="Enter search term", placeholder="e.g., safety, engine, compliance")

    search_button = gr.Button("Search")

    with gr.Row():
        output_md = gr.Markdown()
    
    with gr.Row():
        results_list = gr.Dropdown(label="Select a result to view full context", choices=[])
        context_output = gr.Textbox(label="Full Sentence Context", interactive=False)

    def run_search(files, query):
        table, sentences_list, results = semantic_search(files, query)
        if not sentences_list:
            return table, [], ""
        return table, sentences_list, ""

    def show_context(selection, files, query):
        _, _, results = semantic_search(files, query)
        for r in results:
            if r["file"] in selection and r["sentence"] in selection:
                return f"From {r['file']}:\n\n{r['sentence']} (Relevance: {r['score']}%)"
        return "Could not retrieve context."

    search_button.click(
        run_search,
        inputs=[file_input, query_input],
        outputs=[output_md, results_list, context_output]
    )

    results_list.change(
        show_context,
        inputs=[results_list, file_input, query_input],
        outputs=[context_output]
    )

if __name__ == "__main__":
    demo.launch()
