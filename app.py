import gradio as gr
from sentence_transformers import SentenceTransformer

# Load model once for performance
model = SentenceTransformer("all-MiniLM-L6-v2")

# Example function: semantic similarity
def semantic_similarity(text1, text2):
    embeddings = model.encode([text1, text2])
    from numpy import dot
    from numpy.linalg import norm
    similarity = dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))
    return f"{similarity:.4f}"

# Custom CSS for modern look
custom_css = """
body {background-color: #1a1a2e; color: #e0e0e0;}
h1 {color: #00f0ff; text-align: center;}
.gradio-container {border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);}
input, textarea {border-radius: 10px; padding: 10px;}
button {background: #00f0ff; color: #1a1a2e; font-weight: bold; border-radius: 10px;}
button:hover {background: #00c0cc;}
"""

with gr.Blocks(css=custom_css) as demo:
    gr.Markdown("<h1>🔥 Semantic Similarity Checker 🔥</h1>", elem_id="header")

    with gr.Row():
        text1 = gr.Textbox(label="Text 1", placeholder="Enter first sentence...")
        text2 = gr.Textbox(label="Text 2", placeholder="Enter second sentence...")
    
    similarity_output = gr.Textbox(label="Similarity Score")

    btn = gr.Button("Calculate Similarity")
    btn.click(semantic_similarity, inputs=[text1, text2], outputs=[similarity_output])

demo.launch()
