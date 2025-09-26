import streamlit as st

# Page config MUST be first and ONLY Streamlit call at top level
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide"
)

# Now import other modules
import zipfile
import io
from datetime import datetime
import re

def main():
    """Main function - all Streamlit calls happen inside this function"""
    
    # Initialize session state inside main function
    if 'documents' not in st.session_state:
        st.session_state.documents = []
        st.session_state.metadata = []
    
    # Import here to avoid issues
    try:
        from docx import Document
        import PyPDF2
    except ImportError as e:
        st.error(f"Missing dependencies: {e}")
        return
    
    # App title
    st.title("🔍 MeetSearch Pro")
    st.write("Upload and search your meeting minutes")
    
    # File upload section
    st.header("📤 Upload Documents")
    
    uploaded_files = st.file_uploader(
        "Choose PDF or DOCX files",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="You can upload multiple files at once"
    )
    
    if uploaded_files and st.button("Process Documents"):
        process_uploaded_files(uploaded_files)
    
    # Search section
    st.header("🔍 Search Documents")
    
    if st.session_state.documents:
        search_interface()
    else:
        st.info("Please upload documents first to enable search")
    
    # Analytics section
    st.header("📊 Analytics")
    
    if st.session_state.metadata:
        show_analytics()
    else:
        st.info("Upload documents to see analytics")

def process_uploaded_files(uploaded_files):
    """Process uploaded files"""
    documents = []
    metadata = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processing {file.name}...")
        progress_bar.progress((i + 1) / len(uploaded_files))
        
        text = extract_text_from_file(file)
        if text and len(text.strip()) > 0:
            # Basic text analysis
            words = re.findall(r'\w+', text)
            sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
            
            metadata.append({
                'filename': file.name,
                'word_count': len(words),
                'sentence_count': len(sentences),
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
            st.metric("Avg per Doc", total_words // len(documents))
    else:
        st.error("No valid documents could be processed")
    
    progress_bar.empty()
    status_text.empty()

def extract_text_from_file(file):
    """Extract text from PDF or DOCX file"""
    try:
        if file.name.lower().endswith('.pdf'):
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        
        elif file.name.lower().endswith('.docx'):
            from docx import Document
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            return text
    
    except Exception as e:
        st.error(f"Error processing {file.name}: {str(e)}")
        return ""

def search_interface():
    """Search functionality"""
    query = st.text_input(
        "Enter search query:",
        placeholder="Search for keywords, phrases, or concepts..."
    )
    
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
                    st.write(f"**Sentences:** {result['metadata']['sentence_count']}")
                    st.write("**Matching content:**")
                    st.write(result['content'][:1000] + "..." if len(result['content']) > 1000 else result['content'])
        else:
            st.info("No matches found. Try different search terms.")

def show_analytics():
    """Show document analytics"""
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

# This is the key difference - only call main() if this is the main module
if __name__ == "__main__":
    main()