import gradio as gr
import os
import zipfile
import tempfile
import difflib
import re
import uuid

# -------------------------
# Helper functions
# -------------------------
def extract_and_read(file_obj):
    text = ""
    if file_obj.name.endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(file_obj.name, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
                for root, _, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith((".txt", ".md")):
                            with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as infile:
                                text += infile.read() + "\n"
    else:
        with open(file_obj.name, "r", encoding="utf-8", errors="ignore") as infile:
            text = infile.read()
    return text

def highlight_text(text, query):
    """Highlight query words inside text like Google results."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)

def search_documents(files, query):
    if not files or not query.strip():
        return "<p>Please upload files and enter a search term.</p>"
    
    results_html = []
    for file in files:
        content = extract_and_read(file)
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            if query.lower() in line.lower():
                ratio = difflib.SequenceMatcher(None, query.lower(), line.lower()).ratio()
                snippet = highlight_text(line.strip(), query)
                file_display = os.path.basename(file.name)

                # Get surrounding context (5 lines before & after)
                start = max(0, idx-5)
                end = min(len(lines), idx+5)
                context = "\n".join(lines[start:end])
                context = highlight_text(context, query)

                unique_id = uuid.uuid4().hex[:8]

                card_html = f"""
                <div class="result-card">
                    <div class="result-header">
                        {file_display} <span class="meta">Line {idx} • Match {int(ratio*100)}%</span>
                    </div>
                    <div class="result-snippet">
                        {snippet}
                    </div>
                    <button class="expand-btn" onclick="toggleContext('{unique_id}')">View More Context</button>
                    <div id="context-{unique_id}" class="context hidden">
                        <pre>{context}</pre>
                    </div>
                </div>
                """
                results_html.append(card_html)
    
    if not results_html:
        return "<p>No matches found.</p>"
    
    return """
    <script>
    function toggleContext(id) {
        var el = document.getElementById("context-" + id);
        if (el.classList.contains("hidden")) {
            el.classList.remove("hidden");
        } else {
            el.classList.add("hidden");
        }
    }
    </script>
    <div class='results-container'>""" + "".join(results_html) + "</div>"

def extract_text_panel(files):
    """Extract all text from uploaded files and return it nicely formatted."""
    if not files:
        return "<p>Please upload files to extract text.</p>"
    
    sections = []
    for file in files:
        content = extract_and_read(file)
        file_display = os.path.basename(file.name)
        sections.append(f"""
        <div class="extract-card">
            <div class="extract-header">{file_display}</div>
            <pre class="extract-body">{content}</pre>
        </div>
        """)
    
    return "<div class='extract-container'>" + "".join(sections) + "</div>"

# -------------------------
# Custom CSS
# -------------------------
custom_css = """
body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

/* Layout */
.app-container {
    display: flex;
    height: 100vh;
}

.sidebar {
    width: 240px;
    background: #1d1d1f;
    color: #f5f5f7;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.sidebar h2 {
    font-size: 1.2em;
    font-weight: 700;
    margin-bottom: 20px;
}

.sidebar button {
    background: transparent;
    color: inherit;
    border: none;
    text-align: left;
    padding: 10px;
    font-size: 1em;
    cursor: pointer;
    border-radius: 8px;
    transition: background 0.2s ease;
}

.sidebar button:hover, .sidebar button.active {
    background: #2c2c2e;
}

.main-content {
    flex: 1;
    background: #f9f9f9;
    padding: 30px;
    overflow-y: auto;
}

/* Results styling */
.results-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 20px;
}

.result-card {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: all 0.2s ease;
}

.result-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.12);
}

.result-header {
    font-weight: 600;
    margin-bottom: 8px;
    color: #1d1d1f;
}

.result-header .meta {
    font-size: 0.85em;
    color: gray;
    margin-left: 8px;
}

.result-snippet {
    font-size: 0.95em;
    line-height: 1.4;
    color: #333;
}

mark {
    background: #ffeb3b;
    color: black;
    font-weight: 600;
    border-radius: 3px;
    padding: 0 2px;
}

.expand-btn {
    margin-top: 8px;
    background: #007aff;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.85em;
    cursor: pointer;
    transition: background 0.2s ease;
}

.expand-btn:hover {
    background: #005bb5;
}

.context {
    margin-top: 12px;
    background: #f5f5f7;
    padding: 10px;
    border-radius: 8px;
    font-size: 0.9em;
    white-space: pre-wrap;
}

.hidden {
    display: none;
}

/* Extract text styling */
.extract-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.extract-card {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.extract-header {
    font-weight: 600;
    font-size: 1.05em;
    margin-bottom: 10px;
    color: #1d1d1f;
}

.extract-body {
    font-size: 0.9em;
    line-height: 1.5;
    white-space: pre-wrap;
    color: #333;
}
"""

# -------------------------
# Gradio App Layout
# -------------------------
with gr.Blocks(css=custom_css, theme=gr.themes.Soft()) as demo:
    gr.HTML("""
    <div class="app-container">
        <div class="sidebar">
            <h2>TradeSkor</h2>
            <button onclick="showPanel('search')" class="active">Search</button>
            <button onclick="showPanel('extract')">Extract Text</button>
            <button onclick="showPanel('analytics')">Analytics</button>
        </div>
        <div class="main-content">
            <div id="panel-search"></div>
            <div id="panel-extract" style="display:none;"></div>
            <div id="panel-analytics" style="display:none;">
                <h3>Analytics</h3>
                <p>Coming soon: Contractor performance and project analysis.</p>
            </div>
        </div>
    </div>
    <script>
    function showPanel(panel) {
        document.querySelectorAll('.main-content > div').forEach(div => div.style.display = 'none');
        document.getElementById('panel-' + panel).style.display = 'block';
        document.querySelectorAll('.sidebar button').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }
    </script>
    """)

    # Search panel
    with gr.Column(elem_id="panel-search"):
        gr.Markdown("### Document Search")
        with gr.Row():
            file_input = gr.File(
                file_types=[".txt", ".md", ".zip"],
                file_types_display="extension",
                type="file",
                label="Upload Documents",
                file_count="multiple"
            )
            query_input = gr.Textbox(
                label="Search term",
                placeholder="e.g., project schedule, invoice, safety plan"
            )
        search_btn = gr.Button("Search")
        output_box = gr.HTML(label="Search Results")
        search_btn.click(fn=search_documents, inputs=[file_input, query_input], outputs=output_box)

    # Extract text panel
    with gr.Column(elem_id="panel-extract", visible=False):
        gr.Markdown("### Extract Text")
        file_input_extract = gr.File(
            file_types=[".txt", ".md", ".zip"],
            file_types_display="extension",
            type="file",
            label="Upload Documents",
            file_count="multiple"
        )
        extract_btn = gr.Button("Extract All Text")
        extract_output = gr.HTML(label="Extracted Text")
        extract_btn.click(fn=extract_text_panel, inputs=file_input_extract, outputs=extract_output)

if __name__ == "__main__":
    demo.launch()
