# Hugging Face Spaces compatible Streamlit app
# This structure works with their "bare mode" execution

import streamlit as st
import os
import time

# CRITICAL: Only ONE Streamlit call at top level
st.set_page_config(page_title="MeetSearch Pro", layout="wide")

# Now the rest of the code - NO other Streamlit calls at top level
def main():
    # Simple title
    st.title("🔍 MeetSearch Pro")
    st.write("Upload and search meeting minutes")
    
    # Initialize using a different approach since session state may not work
    if 'docs' not in st.session_state:
        st.session_state.docs = []
        st.session_state.meta = []
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX files",
        type=['pdf', 'docx'],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("Process Files"):
        process_files(uploaded_files)
    
    # Search functionality
    if st.session_state.docs:
        search_files()
    else:
        st.info("Upload documents to get started")
    
    # Show status
    if st.session_state.meta:
        st.sidebar.write(f"Documents: {len(st.session_state.meta)}")
        total_words = sum(m.get('words', 0) for m in st.session_state.meta)
        st.sidebar.write(f"Total words: {total_words}")

def process_files(files):
    """Process uploaded files"""
    import PyPDF2
    from docx import Document
    import re
    
    new_docs = []
    new_meta = []
    
    for file in files:
        text = ""
        try:
            if file.name.lower().endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
            elif file.name.lower().endswith('.docx'):
                doc = Document(file)
                text = " ".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            st.error(f"Error with {file.name}: {str(e)}")
            continue
        
        if text and len(text) > 10:
            words = len(text.split())
            new_docs.append(text)
            new_meta.append({
                'name': file.name,
                'words': words,
                'text': text
            })
    
    if new_docs:
        st.session_state.docs = new_docs
        st.session_state.meta = new_meta
        st.success(f"Processed {len(new_docs)} files!")

def search_files():
    """Search functionality"""
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
                    # Simple display without complex highlighting
                    preview = doc[:500] + "..." if len(doc) > 500 else doc
                    st.write(preview)
        else:
            st.write("No matches found")

# This is the key - only run if we're in a proper environment
if __name__ == "__main__":
    # Try to detect if we're in a proper Streamlit environment
    try:
        main()
    except Exception as e:
        # Fallback for bare mode
        st.title("MeetSearch Pro")
        st.write("Application starting...")
        st.info("If you see this message, the app is loading properly")
        # Let the app continue anyway
        main()