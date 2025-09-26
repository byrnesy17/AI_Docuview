import gradio as gr
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

try:
    from docx import Document
    import PyPDF2
except ImportError:
    print("Missing dependencies")

class DocumentSearch:
    def __init__(self):
        self.documents = []
        self.metadata = []
    
    def extract_text(self, file):
        """Extract text from PDF or DOCX"""
        try:
            if file.name.lower().endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                return " ".join([page.extract_text() or "" for page in reader.pages])
            elif file.name.lower().endswith('.docx'):
                doc = Document(file)
                return " ".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            return f"Error: {str(e)}"
        return ""
    
    def process_files(self, files):
        """Process uploaded files"""
        self.documents = []
        self.metadata = []
        
        for file in files:
            text = self.extract_text(file)
            if text and not text.startswith("Error") and len(text) > 10:
                words = len(re.findall(r'\w+', text))
                sentences = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
                
                self.metadata.append({
                    'filename': file.name,
                    'word_count': words,
                    'sentence_count': sentences,
                    'content': text
                })
                self.documents.append(text)
        
        return f"✅ Processed {len(self.documents)} documents"
    
    def search_documents(self, query):
        """Search through documents"""
        if not self.documents or not query:
            return "No documents or query provided"
        
        results = []
        query_lower = query.lower()
        
        for i, (doc, meta) in enumerate(zip(self.documents, self.metadata)):
            if query_lower in doc.lower():
                # Simple highlighting
                highlighted = doc.replace(query, f"**{query}**")
                results.append(f"📄 {meta['filename']} ({meta['word_count']} words)\n{highlighted[:500]}...")
        
        if results:
            return "\n\n".join(results)
        else:
            return "No matches found"
    
    def get_stats(self):
        """Get document statistics"""
        if not self.metadata:
            return "No documents loaded"
        
        total_docs = len(self.metadata)
        total_words = sum(m['word_count'] for m in self.metadata)
        avg_words = total_words // total_docs if total_docs > 0 else 0
        
        return f"Documents: {total_docs}\nTotal Words: {total_words}\nAverage: {avg_words} words/doc"

# Create the search engine
search_engine = DocumentSearch()

# Create Gradio interface
with gr.Blocks(title="MeetSearch Pro", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🔍 MeetSearch Pro")
    gr.Markdown("Upload and search meeting minutes")
    
    with gr.Tab("Upload"):
        file_input = gr.File(file_count="multiple", file_types=[".pdf", ".docx"], label="Upload PDF or DOCX files")
        upload_btn = gr.Button("Process Documents")
        upload_output = gr.Textbox(label="Status", interactive=False)
        
        upload_btn.click(
            fn=search_engine.process_files,
            inputs=file_input,
            outputs=upload_output
        )
    
    with gr.Tab("Search"):
        search_input = gr.Textbox(label="Search Query", placeholder="Enter keywords to search for...")
        search_btn = gr.Button("Search")
        search_output = gr.Textbox(label="Results", lines=10, interactive=False)
        
        search_btn.click(
            fn=search_engine.search_documents,
            inputs=search_input,
            outputs=search_output
        )
    
    with gr.Tab("Analytics"):
        stats_btn = gr.Button("Show Statistics")
        stats_output = gr.Textbox(label="Document Statistics", interactive=False)
        
        stats_btn.click(
            fn=search_engine.get_stats,
            inputs=[],
            outputs=stats_output
        )

# Launch the app
if __name__ == "__main__":
    demo.launch(share=True)