import gradio as gr
from sentence_transformers import SentenceTransformer

# Load the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to handle file input and compute embeddings
def process_file(file):
    if file is None:
        return "No file provided"
    text = file.read().decode("utf-8")  # assuming it's a text file
    embeddings = model.encode(text)
    return embeddings.tolist()

# Gradio interface
iface = gr.Interface(
    fn=process_file,
    inputs=gr.File(label="Upload a text file"),
    outputs=gr.Textbox(label="Embeddings")
)

# Launch the app
iface.launch()
