import gradio as gr
import uuid
import html

# Keep track of uploaded files
uploaded_files = []

# Mock AI search function
def search_documents(query):
    results = []
    for idx, f in enumerate(uploaded_files):
        results.append({
            "id": f["id"],
            "fileName": f["name"],
            "highlighted": f"This is a sample match for <mark style='background: rgba(16, 185, 129, 0.2); padding:2px 4px; border-radius:4px;font-weight:600;'>{html.escape(query)}</mark> in {f['name']}.",
            "score": round(0.7 + 0.3*idx/len(uploaded_files), 2)
        })
    return results

# Upload handler
def handle_upload(files):
    global uploaded_files
    for file in files:
        uploaded_files.append({"id": str(uuid.uuid4()), "name": file.name, "file": file})
    return update_file_list()

# Remove file
def remove_file(file_id):
    global uploaded_files
    uploaded_files = [f for f in uploaded_files if f["id"] != file_id]
    return update_file_list()

# Update uploaded file list HTML
def update_file_list():
    if not uploaded_files:
        return "<p>No files uploaded.</p>"
    html_files = ""
    for f in uploaded_files:
        icon = "📄" if f['name'].endswith(('.pdf','.docx','.txt')) else "🗜️"
        html_files += f"<div class='glass' style='display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;'>"
        html_files += f"<span>{icon} {f['name']}</span>"
        html_files += f"</div>"
    return html_files

# Perform search
def perform_search(query):
    if not query.strip():
        return "<p>No query entered</p>"
    results = search_documents(query)
    html_results = ""
    for idx, r in enumerate(results):
        color = "#34d399" if r["score"]>=0.8 else "#facc15" if r["score"]>=0.65 else "#3b82f6"
        label = "High Match" if r["score"]>=0.8 else "Good Match" if r["score"]>=0.65 else "Relevant"
        html_results += f"<div class='glass' style='margin-bottom:8px;'>"
        html_results += f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
        html_results += f"<h4>{r['fileName']} - Match #{idx+1}</h4>"
        html_results += f"<span class='badge' style='background:{color};'>{label} ({int(r['score']*100)}%)</span>"
        html_results += f"</div>"
        html_results += f"<p>{r['highlighted']}</p>"
        html_results += "</div>"
    return html_results

# Gradio UI
with gr.Blocks(css="""
/* Gradient background */
body { background: linear-gradient(135deg, hsl(220,26%,14%), hsl(215,25%,27%)); font-family: sans-serif; color: hsl(213,31%,91%); margin:0; padding:20px;}
.glass { backdrop-filter: blur(12px); background: hsla(224,27%,9%,0.8); border:1px solid hsla(214,32%,91%,0.2); padding:20px; border-radius:8px; }
.badge { display:inline-block; padding:2px 6px; border-radius:6px; margin-left:4px; font-size:12px; color:#000;}
.row { display:flex; flex-wrap:wrap; gap:20px;}
.column { flex:1; min-width:300px;}
.upload-btn { margin-bottom:10px;}
""") as demo:

    gr.HTML("<h1 style='text-align:center;'>AI Document Search</h1>")
    gr.HTML("<p style='text-align:center;'>Upload documents and search with AI-powered semantic understanding</p>")

    with gr.Row():
        with gr.Column():
            upload_files = gr.File(file_types=[".pdf",".docx",".txt",".zip"], file_types_multiple=True, label="Upload Documents")
            search_input = gr.Textbox(label="Search Query", placeholder="Enter search terms...")
            search_btn = gr.Button("Search Documents", elem_id="search-btn")
            file_list = gr.HTML(update_file_list, elem_id="file-list")

        with gr.Column():
            search_results = gr.HTML("<p>Results will appear here.</p>", elem_id="search-results")

    upload_files.upload(handle_upload, upload_files, file_list)
    search_btn.click(perform_search, search_input, search_results)

demo.launch()
