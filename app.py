#!/usr/bin/env python3
"""
MeetSearch Pro - Forces proper Streamlit initialization
"""

import os
import sys

# CRITICAL: Force Streamlit to initialize properly
# This mimics what 'streamlit run' does internally
if not hasattr(sys, '_MEIPASS'):
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import Streamlit
import streamlit as st
from streamlit.web import cli as stcli
from streamlit import runtime

# Check if we're running in bare mode and force proper initialization
if runtime.exists():
    # We're in a proper Streamlit runtime
    print("Running in proper Streamlit runtime")
else:
    # We're in bare mode - try to force proper initialization
    print("Detected bare mode - attempting to initialize properly")
    # This is a hack to force Streamlit to initialize its runtime context
    if not hasattr(st, '_is_running_with_streamlit'):
        st._is_running_with_streamlit = True

# NOW set page config - this should work properly
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import other dependencies after Streamlit is properly initialized
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

try:
    from docx import Document
    import PyPDF2
    DEPS_OK = True
except ImportError as e:
    DEPS_OK = False
    st.error(f"Missing dependencies: {e}")

# Initialize session state properly
if 'initialized' not in st.session_state:
    st.session_state.update({
        'initialized': True,
        'documents': [],
        'metadata': [],
        'search_results': []
    })

# Main app function
def main():
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #2563eb;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)
    
    # Use tabs for navigation
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔍 Search", "📊 Analytics"])
    
    with tab1:
        render_upload()
    
    with tab2:
        render_search()
    
    with tab3:
        render_analytics()

def render_upload():
    st.header("Upload Meeting Minutes")
    
    uploaded_files = st.file_uploader(
        "Select PDF or DOCX files",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="You can upload multiple files at once"
    )
    
    if uploaded_files and st.button("Process Documents", type="primary"):
        process_files(uploaded_files)

def process_files(uploaded_files):
    documents = []
    metadata = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processing {file.name}...")
        progress_bar.progress((i + 1) / len(uploaded_files))
        
        text = ""
        try:
            if file.name.lower().endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
            elif file.name.lower().endswith('.docx'):
                doc = Document(file)
                text = " ".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
            continue
        
        if text and len(text.strip()) > 10:
            words = len(re.findall(r'\w+', text))
            sentences = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
            
            metadata.append({
                'filename': file.name,
                'word_count': words,
                'sentence_count': sentences,
                'file_size': len(file.getvalue()),
                'upload_time': datetime.now(),
                'content': text
            })
            documents.append(text)
    
    if documents:
        st.session_state.documents = documents
        st.session_state.metadata = metadata
        st.success(f"✅ Successfully processed {len(documents)} documents!")
        
        # Show quick stats
        col1, col2, col3 = st.columns(3)
        total_words = sum(m['word_count'] for m in metadata)
        
        with col1:
            st.metric("Documents", len(documents))
        with col2:
            st.metric("Total Words", total_words)
        with col3:
            st.metric("Average per Doc", total_words // len(documents))
    else:
        st.error("No valid documents could be processed")
    
    progress_bar.empty()
    status_text.empty()

def render_search():
    st.header("Search Documents")
    
    if not st.session_state.documents:
        st.info("Please upload documents first to enable search")
        return
    
    query = st.text_input("Search query:", placeholder="Enter keywords to search for...")
    
    if query and query.strip():
        results = []
        query_lower = query.lower()
        
        for i, (doc, meta) in enumerate(zip(st.session_state.documents, st.session_state.metadata)):
            if query_lower in doc.lower():
                # Simple highlighting
                highlighted = doc.replace(query, f"**{query}**")
                results.append({
                    'filename': meta['filename'],
                    'content': highlighted,
                    'metadata': meta,
                    'match_count': doc.lower().count(query_lower)
                })
        
        if results:
            st.success(f"Found {len(results)} matching documents")
            
            for result in results:
                with st.expander(f"📄 {result['filename']} ({result['match_count']} matches)"):
                    st.write(f"**Word count:** {result['metadata']['word_count']}")
                    st.write("**Matching content:**")
                    st.write(result['content'][:1000] + "..." if len(result['content']) > 1000 else result['content'])
        else:
            st.info("No matches found. Try different search terms.")

def render_analytics():
    st.header("Document Analytics")
    
    if not st.session_state.metadata:
        st.info("Upload documents to see analytics")
        return
    
    metadata = st.session_state.metadata
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", len(metadata))
    
    with col2:
        total_words = sum(m['word_count'] for m in metadata)
        st.metric("Total Words", f"{total_words:,}")
    
    with col3:
        avg_words = total_words // len(metadata)
        st.metric("Avg Words/Doc", f"{avg_words:,}")
    
    with col4:
        total_size = sum(m['file_size'] for m in metadata)
        st.metric("Total Size", f"{total_size / 1024 / 1024:.2f} MB")
    
    # Document list
    st.subheader("Document Details")
    for meta in metadata:
        with st.expander(f"{meta['filename']} ({meta['word_count']} words)"):
            st.write(f"**Uploaded:** {meta['upload_time'].strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**File size:** {meta['file_size']:,} bytes")
            st.write(f"**Sentences:** {meta['sentence_count']}")
            st.write("**Preview:**")
            st.text(meta['content'][:300] + "..." if len(meta['content']) > 300 else meta['content'])

# Run the app
if __name__ == "__main__":
    # Force proper execution context
    if not runtime.exists():
        # If we're not in a proper runtime, try to initialize one
        try:
            # This is a hack to force proper initialization
            st._is_running_with_streamlit = True
            if hasattr(st, 'session_state'):
                # Force session state initialization
                if not hasattr(st.session_state, '_initialized'):
                    st.session_state._initialized = True
        except:
            pass
    
    main()