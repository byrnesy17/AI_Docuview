from fastapi import FastAPI
from gradio import Interface
import gradio as gr

app = FastAPI()

def process_document(file):
    # Your document processing logic here
    return "Processed content"

iface = Interface(fn=process_document, inputs=gr.File(), outputs=gr.Textbox())

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Document Processing API"}

@app.on_event("startup")
async def startup_event():
    iface.launch(share=True)

