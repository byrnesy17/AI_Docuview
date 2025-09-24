import gradio as gr
import os
import zipfile
import docx
from PyPDF2 import PdfReader
import nltk
from nltk.corpus import wordnet
import re

# Make sure nltk data is available
nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)

# -------------------------------
# Document Processing
# -------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text += f"\n[PDF READ ERROR: {file_path} | {e}]"
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text += f"\n[DOCX READ ERROR: {file_path} | {e}]"
    return text

def extract_text_from_zip(file_path):
    text = ""
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".pdf"):
                    with z.open(name) as f:
                        tmp_path = f"/tmp/{os.path.basename(name)}"
                        with open(tmp_path, "wb") as tmpf:
                            tmpf.write(f.read())
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_pdf(tmp_path)
                elif name.endswith(".docx"):
                    with z.open(name) as f:
                        tmp_path = f"/tmp/{os.path.basename(name)}"
                        with open(tmp_path, "wb") as tmpf:
                            tmpf.write(f.read())
                        text += f"\n--- {name} ---\n"
                        text += extract_text_from_docx(tmp_path)
    except Exception as e:
        text += f"\n[ZIP READ ERROR: {file_path} | {e}]"
    return text

def load_documents(files):
    all_texts = {}
    for file_path in files:
        if file_path.endswith(".pdf"):
            all_texts[file_path] = extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            all_texts[file_path] = extract_text_from_docx(file_path)
        elif file_path.endswith(".zip"):
            all_texts[file_path] = extract_text_from_zip(file_path)
        else:
            all_texts[file_path] = f"[Unsupported file type: {file_path}]"
    return all_texts

# -------------------------------
# Smart Query Expansion
# -------------------------------
def expand_query(query):
    """Expand search query to include synonyms and related words."""
    expanded = {query.lower()}
    for syn in wordnet.synsets(query):
        for lemma in syn.lemmas():
            expanded.add(lemma.name().lower().replace("_", " "))
    return expanded

# -------------------------------
# Highlight matches
# -------------------------------
def highlight_text(text, keywords):
    """Highlight all occurrences of keywords in text."""
    for kw in sorted(keywords, key=len, reverse=True):  # longer words first
        regex = re.compile(rf"\b({re.escape(kw)})\b", re.IGNORECASE)
        text = regex.sub(r"**🟨\1🟨**", text)
    return text

# -------------------------------
# Search Function
# -------------------------------
def search_documents(files, query):
    if not files or not query.strip():
        return "⚠️ Please upload documents and enter a search query."

    documents = load_documents(files)
    results = []

    # Expand query with synonyms
    keywords = expand_query(query)

    for fname, text in documents.items():
        if not text.strip():
            continue

        lines = text.split("\n")
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in keywords):
                snapshot = "\n".join(lines[max(0, i-1): min(len(lines), i+2)])
                highlighted = highlight_text(snapshot, keywords)
                results.append(
                    f"📄 **{os.path.basename(fname)}** — line {i+1}\n\n{highlighted}"
                )

    if not results:
        return f"❌ No matches (or close matches) found for: **{query}**"
    return "\n\n---\n\n".join(results)

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 📂 Smart Document Search  
        Upload PDFs, Word files, or ZIPs — then search across them.  
        Results show **context snapshots** where your word *or related words* appear,  
        with matches highlighted 🟨.
        """
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            type="filepath",
            file_types=[".pdf", ".docx", ".zip"],
            file_types_multiple=True   # ✅ correct for multiple files
        )

    with gr.Row():
        query = gr.Textbox(label="🔍 Search Query", placeholder="Enter a word or phrase...")

    search_btn = gr.Button("Search", variant="primary")
    output = gr.Markdown()

    search_btn.click(fn=search_documents, inputs=[file_input, query], outputs=output)

# -------------------------------
# Launch
# -------------------------------
if __name__ == "__main__":
    demo.launch()
