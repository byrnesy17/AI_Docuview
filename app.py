import gradio as gr
import os
import tempfile
from docx import Document
from pypdf import PdfReader
import zipfile
from sentence_transformers import SentenceTransformer, util
import nltk
from nltk.corpus import wordnet

# Download WordNet if not already
nltk.download('wordnet')

# Initialize semantic model (adjust model for performance)
semantic_model = SentenceTransformer('all-MiniLM-L6-v2')

# Extract text from PDF or DOCX
def extract_text_with_pages(file_path):
    text_data = []
    if file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                for line in text.split("\n"):
                    if line.strip():
                        text_data.append((i + 1, line.strip()))
    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                text_data.append((None, p.text.strip()))
    return text_data

# Expand search keywords using WordNet
def expand_keywords(keyword):
    synonyms = set()
    synonyms.add(keyword)
    for syn in wordnet.synsets(keyword):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))
    return list(synonyms)

# Search documents (with semantic similarity)
def search_documents(files, keyword):
    results = ""
    temp_dir = tempfile.mkdtemp()
    all_files = []

    # Ensure files is a list
    if not isinstance(files, list):
        files = [files]

    # Expand keyword list
    keywords = expand_keywords(keyword)

    # Extract files from zip or add directly
    for file in files:
        if file.lower().endswith(".zip"):
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                for root, _, filenames in os.walk(temp_dir):
                    for f in filenames:
                        if f.lower().endswith((".pdf", ".docx")):
                            all_files.append(os.path.join(root, f))
        else:
            all_files.append(file)

    # Process each file
    for file_path in all_files:
        text_data = extract_text_with_pages(file_path)
        matches = []
        for page_num, line in text_data:
            # Check semantic similarity
            for k in keywords:
                similarity = util.cos_sim(
                    semantic_model.encode(k, convert_to_tensor=True),
                    semantic_model.encode(line, convert_to_tensor=True)
                ).item()
                if similarity >= 0.75:  # threshold for match
                    if page_num:
                        matches.append(f"(Page {page_num}, Sim={similarity:.2f}) {line}")
                    else:
                        matches.append(f"(Sim={similarity:.2f}) {line}")
                    break  # no need to check other keywords for this line
        if matches:
            results += f"--- {os.path.basename(file_path)} ---\n"
            results += "\n".join(matches) + "\n\n"

    if results == "":
        results = "No matches found."
    return results

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("<h1>Document Keyword & Semantic Search</h1>")
    gr.Markdown("Upload PDF, Word, or ZIP files. The search will find exact and related words.")
    
    with gr.Row():
        file_input = gr.File(label="Upload Documents", file_types=[".pdf", ".docx", ".zip"], file_types_multiple=True)
        keyword_input = gr.Textbox(label="Keyword to search")
    
    search_button = gr.Button("Search")
    results_output = gr.Textbox(label="Search Results", lines=20)

    search_button.click(search_documents, inputs=[file_input, keyword_input], outputs=results_output)

demo.launch()
