import gradio as gr
from PyPDF2 import PdfReader
import docx
import os
from PIL import Image, ImageDraw, ImageFont
import tempfile

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif ext == ".docx":
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    else:
        text = ""
    return text

def highlight_term_in_text(text, term):
    results = []
    term_lower = term.lower()
    for line in text.splitlines():
        if term_lower in line.lower():
            results.append(line.strip())
    return results

def create_highlight_image(sentence, term):
    font_size = 20
    font = ImageFont.load_default()
    lines = [sentence]

    # Calculate image size
    width = max([font.getsize(line)[0] for line in lines]) + 20
    height = len(lines) * (font.getsize(lines[0])[1] + 10) + 20

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    y_text = 10
    for line in lines:
        start = line.lower().find(term.lower())
        if start != -1:
            # Draw text before term
            draw.text((10, y_text), line[:start], fill='black', font=font)
            # Draw highlighted term
            term_width = font.getsize(line[start:start+len(term)])[0]
            draw.rectangle([10 + font.getsize(line[:start])[0], y_text, 10 + font.getsize(line[:start])[0]+term_width, y_text+font.getsize(line[start:start+len(term)])[1]], fill='yellow')
            draw.text((10 + font.getsize(line[:start])[0], y_text), line[start:start+len(term)], fill='black', font=font)
            # Draw rest of line
            draw.text((10 + font.getsize(line[:start+len(term)])[0], y_text), line[start+len(term):], fill='black', font=font)
        else:
            draw.text((10, y_text), line, fill='black', font=font)
        y_text += font.getsize(line)[1] + 10

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file.name)
    return temp_file.name

def search_files(files, term):
    output = []
    images = []
    for f in files:
        text = extract_text(f.name)
        sentences = highlight_term_in_text(text, term)
        for s in sentences:
            img_path = create_highlight_image(s, term)
            output.append(f"{os.path.basename(f.name)}: {s}")
            images.append(img_path)
    return output, images

with gr.Blocks() as demo:
    gr.Markdown("## Document Search Tool")
    with gr.Row():
        file_input = gr.File(
            label="Upload Documents",
            file_types=[".pdf", ".docx", ".zip"],
            file_types_multiple=False  # remove old param
        )
        search_term = gr.Textbox(label="Search Term")
    search_btn = gr.Button("Search")
    results = gr.Dataframe(headers=["Results"], interactive=False)
    result_images = gr.Gallery(label="Highlighted Text").style(grid=[1], height="auto")

    search_btn.click(
        fn=search_files,
        inputs=[file_input, search_term],
        outputs=[results, result_images]
    )

demo.launch()
