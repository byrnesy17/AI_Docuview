import gradio as gr
from pathlib import Path
import zipfile
import PyPDF2
import docx

# -------------------------
# File processing functions
# -------------------------

def read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def read_txt(file):
    return file.read().decode("utf-8")

def extract_zip(file):
    texts = []
    with zipfile.ZipFile(file) as z:
        for name in z.namelist():
            with z.open(name) as f:
                if name.endswith(".pdf"):
                    texts.append(read_pdf(f))
                elif name.endswith(".docx") or name.endswith(".doc"):
                    texts.append(read_docx(f))
                elif name.endswith(".txt"):
                    texts.append(read_txt(f))
    return "\n".join(texts)

def read_file(file):
    if file.name.endswith(".pdf"):
        return read_pdf(file)
    elif file.name.endswith(".docx") or file.name.endswith(".doc"):
        return read_docx(file)
    elif file.name.endswith(".txt"):
        return read_txt(file)
    elif file.name.endswith(".zip"):
        return extract_zip(file)
    return ""

# -------------------------
# AI search simulation
# -------------------------

def ai_search(files, query):
    results = []
    if not files or not query:
        return "Upload files and enter a search query."

    for f in files:
        content = read_file(f)
        score = 0
        highlighted = ""
        if query.lower() in content.lower():
            snippet = content.lower().split(query.lower())[0][-50:] + query + content.lower().split(query.lower())[1][:50]
            highlighted = snippet.replace(
                query,
                f"<mark style='background: rgba(16, 185, 129, 0.2); padding: 2px 4px; border-radius: 4px; font-weight:600;'>{query}</mark>"
            )
            score = 0.8 + 0.2 * (hash(f.name) % 100) / 100  # Random-ish score for demo
        else:
            highlighted = f"No match found for '{query}'."
            score = 0.5

        # Assign label based on score
        if score >= 0.8:
            label = f"High Match ({int(score*100)}%)"
            color = "#16a34a"  # green
        elif score >= 0.65:
            label = f"Good Match ({int(score*100)}%)"
            color = "#eab308"  # yellow
        else:
            label = f"Relevant ({int(score*100)}%)"
            color = "#3b82f6"  # blue

        results.append({
            "file": f.name,
            "highlighted": highlighted,
            "score": score,
            "label": label,
            "color": color
        })

    # Build HTML grid
    html = "<div style='display:grid; grid-template-columns: repeat(auto-fill, minmax(300px,1fr)); gap:20px;'>"
    for r in results:
        html += f"""
        <div style='background: rgba(20,20,30,0.7); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.1);'>
            <h4 style='margin:0 0 5px 0;'>{r['file']}</h4>
            <span style='background:{r['color']}33; color:{r['color']}; padding:2px 6px; border-radius:4px; font-weight:600;'>{r['label']}</span>
            <p style='margin-top:10px; background: rgba(255,255,255,0.05); padding:8px; border-left:3px solid {r['color']}; border-radius:4px;'>{r['highlighted']}</p>
        </div>
        """
    html += "</div>"
    return html

# -------------------------
# Gradio App
# -------------------------

css_styles = """
body {background: linear-gradient(135deg, #16203d, #2b2b4f); color: #e6e6e6; font-family: sans-serif;}
.gradio-container {max-width: 1000px; margin:auto;}
input, textarea {background: rgba(0,0,0,0.2); color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding:10px;}
button {background: linear-gradient(135deg, #1d4ed8, #22d3ee); color:#fff; border:none; border-radius:6px; padding:10px 20px; cursor:pointer;}
mark {background: rgba(16, 185, 129, 0.2); padding: 2px 4px; border-radius: 4px; font-weight:600;}
"""

with gr.Blocks(css=css_styles) as demo:
    gr.Markdown("<h1 style='text-align:center'>🤖 AI Document Search</h1>")
    gr.Markdown("<p style='text-align:center'>Upload PDF, DOCX, TXT, or ZIP files and search with AI-powered semantic search.</p>")

    with gr.Row():
        files = gr.File(label="Upload Documents", file_types=[".pdf",".docx",".txt",".zip"], file_types_allow_multiple=True)
    
    query = gr.Textbox(label="Search Query", placeholder="Type your search term here...")
    
    search_btn = gr.Button("Search")
    
    output = gr.HTML()

    search_btn.click(ai_search, inputs=[files, query], outputs=output)

demo.launch()
