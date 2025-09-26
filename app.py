import streamlit as st
import zipfile
import io
from datetime import datetime
import re

# ONLY THIS at top level - no session state, no other calls
st.set_page_config(page_title="MeetSearch Pro", layout="wide")

# Import doc processing
try:
    from docx import Document
    import PyPDF2
except ImportError:
    st.error("Missing dependencies")

# Use a GLOBAL variable instead of session state
app_data = {
    'documents': [],
    'metadata': []
}

def extract_text(file):
    """Extract text from file"""
    try:
        if file.name.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return " ".join([page.extract_text() or "" for page in reader.pages])
        elif file.name.lower().endswith('.docx'):
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs if p.text])
    except:
        return ""
    return ""

def main():
    """Main app - no session state usage"""
    st.title("🔍 MeetSearch Pro")
    st.write("Upload and search meeting minutes")
    
    # Upload section
    st.header("📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Choose PDF or DOCX files", 
        type=['pdf', 'docx'], 
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("Process Files"):
        # Process files and update global data
        new_docs = []
        new_meta = []
        
        for file in uploaded_files:
            text = extract_text(file)
            if text and len(text) > 10:
                words = len(text.split())
                new_docs.append(text)
                new_meta.append({
                    'name': file.name,
                    'words': words,
                    'text': text
                })
        
        if new_docs:
            app_data['documents'] = new_docs
            app_data['metadata'] = new_meta
            st.success(f"✅ Processed {len(new_docs)} documents!")
    
    # Search section
    st.header("🔍 Search Documents")
    
    if app_data['documents']:
        query = st.text_input("Search for:")
        if query:
            results = []
            for i, (doc, meta) in enumerate(zip(app_data['documents'], app_data['metadata'])):
                if query.lower() in doc.lower():
                    # Simple highlight
                    highlighted = doc.replace(query, f"**{query}**")
                    results.append((meta['name'], highlighted, meta))
            
            if results:
                st.success(f"Found {len(results)} matches:")
                for name, highlighted, meta in results:
                    with st.expander(f"📄 {name} - {meta['words']} words"):
                        st.write(highlighted)
            else:
                st.info("No matches found")
    else:
        st.info("Upload documents to enable search")
    
    # Analytics section
    st.header("📊 Analytics")
    
    if app_data['metadata']:
        meta = app_data['metadata']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Documents", len(meta))
        with col2:
            total_words = sum(m['words'] for m in meta)
            st.metric("Total Words", total_words)
        with col3:
            avg_words = total_words // len(meta) if meta else 0
            st.metric("Avg per Doc", avg_words)
        
        # Show document list
        for m in meta:
            with st.expander(f"{m['name']} ({m['words']} words)"):
                st.write(m['text'][:500] + "..." if len(m['text']) > 500 else m['text'])
    else:
        st.info("Upload documents to see analytics")

# Run the app
if __name__ == "__main__":
    main()