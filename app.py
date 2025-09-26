import streamlit as st

# ABSOLUTE FIRST - Page config must be first and ONLY Streamlit call at top
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide"
)

# Now import everything else
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

# Import document libraries
try:
    from docx import Document
    import PyPDF2
except ImportError:
    st.error("Required packages not installed")

# Initialize session state AFTER imports
if 'docs' not in st.session_state:
    st.session_state.docs = []
    st.session_state.meta = []

# Simple functions
def extract_text(file):
    if file.name.lower().endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(file)
            return " ".join([page.extract_text() or "" for page in reader.pages])
        except:
            return ""
    elif file.name.lower().endswith('.docx'):
        try:
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs if p.text])
        except:
            return ""
    return ""

# Main app - SIMPLE and DIRECT
st.title("🔍 MeetSearch Pro")
st.write("Upload PDF or Word documents to search")

# File upload
uploaded_files = st.file_uploader(
    "Choose files", 
    type=['pdf', 'docx'], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Process Files"):
        new_docs = []
        new_meta = []
        for file in uploaded_files:
            text = extract_text(file)
            if text and len(text) > 10:
                new_docs.append(text)
                new_meta.append({
                    'name': file.name,
                    'words': len(text.split()),
                    'date': datetime.now()
                })
        
        if new_docs:
            st.session_state.docs = new_docs
            st.session_state.meta = new_meta
            st.success(f"Processed {len(new_docs)} files!")

# Search
if st.session_state.docs:
    query = st.text_input("Search for:")
    if query:
        results = []
        for i, (doc, meta) in enumerate(zip(st.session_state.docs, st.session_state.meta)):
            if query.lower() in doc.lower():
                results.append((meta['name'], doc, meta))
        
        if results:
            st.write(f"Found {len(results)} matches:")
            for name, doc, meta in results:
                with st.expander(f"{name} - {meta['words']} words"):
                    # Simple highlight
                    highlighted = doc.replace(query, f"**{query}**")
                    st.write(highlighted)
        else:
            st.write("No matches found")

# Show status
if st.session_state.meta:
    st.sidebar.write("**Documents loaded:**", len(st.session_state.meta))
    total_words = sum(m['words'] for m in st.session_state.meta)
    st.sidebar.write("**Total words:**", total_words)
else:
    st.sidebar.write("No documents loaded")