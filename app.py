import streamlit as st
import os
import time

# CRITICAL: This must be the VERY FIRST Streamlit command
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide"
)

# Now import other dependencies
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

try:
    from docx import Document
    import PyPDF2
except ImportError as e:
    st.error(f"Import error: {e}")

# Initialize session state with proper checks
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.documents = []
    st.session_state.metadata = []

# Simple, robust functions
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error reading DOCX: {e}"

def process_files(uploaded_files):
    documents = []
    metadata = []
    
    for uploaded_file in uploaded_files:
        text = ""
        if uploaded_file.name.lower().endswith('.pdf'):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.lower().endswith('.docx'):
            text = extract_text_from_docx(uploaded_file)
        
        if text and not text.startswith("Error"):
            words = re.findall(r'\b\w+\b', text.lower())
            sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
            
            metadata.append({
                'filename': uploaded_file.name,
                'words': len(words),
                'sentences': len(sentences),
                'content': text
            })
            documents.append(text)
    
    return documents, metadata

# Main app layout
st.title("🔍 MeetSearch Pro")
st.write("Upload and search your meeting minutes")

# Simple tab navigation
tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔍 Search", "📊 Analytics"])

with tab1:
    st.header("Upload Documents")
    uploaded_files = st.file_uploader("Choose PDF or DOCX files", 
                                    type=['pdf', 'docx'], 
                                    accept_multiple_files=True)
    
    if uploaded_files and st.button("Process Files"):
        with st.spinner("Processing..."):
            documents, metadata = process_files(uploaded_files)
            if documents:
                st.session_state.documents = documents
                st.session_state.metadata = metadata
                st.success(f"Processed {len(documents)} files!")
            else:
                st.error("No valid documents found")

with tab2:
    st.header("Search Documents")
    
    if not st.session_state.documents:
        st.warning("Please upload documents first")
    else:
        query = st.text_input("Search for:")
        if query:
            results = []
            for i, (doc, meta) in enumerate(zip(st.session_state.documents, st.session_state.metadata)):
                if query.lower() in doc.lower():
                    results.append((i, meta, doc))
            
            if results:
                st.write(f"Found {len(results)} matches:")
                for i, meta, doc in results:
                    with st.expander(meta['filename']):
                        st.write(f"Words: {meta['words']}")
                        st.text_area("Content", doc, height=200)
            else:
                st.write("No matches found")

with tab3:
    st.header("Analytics")
    
    if not st.session_state.metadata:
        st.info("Upload documents to see analytics")
    else:
        total_files = len(st.session_state.metadata)
        total_words = sum(meta['words'] for meta in st.session_state.metadata)
        
        st.metric("Total Files", total_files)
        st.metric("Total Words", total_words)
        st.metric("Average Words", total_words // total_files if total_files > 0 else 0)

# Footer
st.markdown("---")
st.write("MeetSearch Pro - Simple, effective document search")