import streamlit as st
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

# Document processing
from docx import Document
import PyPDF2

# Configure the page FIRST - this is critical for Hugging Face Spaces
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
        border-left: 5px solid #1f77b4;
    }
    .highlight {
        background-color: #ffeb3b;
        padding: 0.1rem 0.2rem;
        border-radius: 3px;
        font-weight: bold;
    }
    .match-score {
        color: #4caf50;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state with safe checks
if 'documents' not in st.session_state:
    st.session_state.documents = []
if 'metadata' not in st.session_state:
    st.session_state.metadata = []

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def simple_text_analysis(text):
    """Perform basic text analysis"""
    words = re.findall(r'\b\w+\b', text.lower())
    word_count = len(words)
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    
    word_freq = Counter(words)
    common_words = word_freq.most_common(10)
    
    return {
        'word_count': word_count,
        'sentence_count': sentence_count,
        'common_words': common_words,
        'sentences': sentences
    }

def process_uploaded_files(uploaded_files):
    """Process uploaded files and extract text"""
    documents = []
    metadata = []
    
    for uploaded_file in uploaded_files:
        text = ""
        if uploaded_file.name.lower().endswith('.pdf'):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.lower().endswith('.docx'):
            text = extract_text_from_docx(uploaded_file)
        else:
            continue
        
        if text and text.strip():
            analysis = simple_text_analysis(text)
            
            metadata.append({
                'filename': uploaded_file.name,
                'upload_date': datetime.now(),
                'file_size': len(uploaded_file.getvalue()),
                'word_count': analysis['word_count'],
                'sentence_count': analysis['sentence_count'],
                'common_words': analysis['common_words'],
                'sentences': analysis['sentences'],
                'content': text
            })
            documents.append(text)
    
    return documents, metadata

def keyword_search(query, documents, metadata, top_k=5):
    """Keyword search with basic matching"""
    if not documents:
        return []
    
    results = []
    query_lower = query.lower()
    query_words = [word for word in query_lower.split() if len(word) > 2]
    
    if not query_words:
        return []
    
    for i, (doc, meta) in enumerate(zip(documents, metadata)):
        match_score = 0
        keyword_sentences = []
        
        for j, sentence in enumerate(meta['sentences']):
            sentence_lower = sentence.lower()
            sentence_score = 0
            highlighted_sentence = sentence
            
            for word in query_words:
                if word in sentence_lower:
                    sentence_score += 1
                    highlighted_sentence = re.sub(
                        f'({re.escape(word)})', 
                        r'<span class="highlight">\1</span>', 
                        highlighted_sentence, 
                        flags=re.IGNORECASE
                    )
            
            if sentence_score > 0:
                keyword_sentences.append({
                    'sentence': highlighted_sentence,
                    'similarity': sentence_score / len(query_words),
                    'position': j
                })
                match_score += sentence_score
        
        if match_score > 0:
            normalized_score = min(match_score / (len(query_words) * 3), 1.0)
            results.append({
                'document': doc,
                'metadata': meta,
                'score': normalized_score,
                'matches': keyword_sentences[:5]
            })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center;">
        <h1>🔍 MeetSearch Pro</h1>
        <p>Smart Meeting Minutes Search</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Use selectbox instead of radio for better compatibility
    page = st.selectbox(
        "Navigate to:",
        ["Dashboard", "Upload", "Search", "Analytics"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### Quick Stats")
    
    metadata = st.session_state.metadata
    if metadata:
        st.info(f"📊 Documents: {len(metadata)}")
        total_words = sum(meta['word_count'] for meta in metadata)
        st.success(f"📝 Total Words: {total_words:,}")
    else:
        st.info("📊 Documents: 0")
        st.success("📝 Total Words: 0")

# Main content based on page selection
if page == "Dashboard":
    st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🚀 Smart Search</h3>
            <p>Find exactly what you need in your meeting minutes.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 Document Insights</h3>
            <p>Get valuable analytics from your meetings.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>💾 Multi-Format</h3>
            <p>Upload PDF and Word documents easily.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 🚀 Get Started")
    
    steps = [
        "1. **Upload** your meeting minutes in the Upload section",
        "2. **Search** for specific terms in the Search section", 
        "3. **View** highlighted results with context"
    ]
    
    for step in steps:
        st.markdown(step)
    
    metadata = st.session_state.metadata
    if metadata:
        st.markdown("---")
        st.markdown("## 📈 Current Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Documents Loaded", len(metadata))
        with col2:
            total_words = sum(meta['word_count'] for meta in metadata)
            st.metric("Total Words", f"{total_words:,}")
        with col3:
            avg_words = total_words // len(metadata)
            st.metric("Average per Doc", f"{avg_words:,}")

elif page == "Upload":
    st.markdown("## 📤 Upload Meeting Minutes")
    
    upload_option = st.radio("Upload method:", ["Single Files", "ZIP Folder"], horizontal=True)
    
    uploaded_files = []
    
    if upload_option == "Single Files":
        uploaded_files = st.file_uploader(
            "Upload PDF or Word documents",
            type=['pdf', 'docx'],
            accept_multiple_files=True
        )
    else:
        zip_file = st.file_uploader("Upload ZIP folder", type=['zip'])
        
        if zip_file:
            with zipfile.ZipFile(zip_file, 'r') as z:
                for file_info in z.infolist():
                    if file_info.filename.lower().endswith(('.pdf', '.docx')):
                        with z.open(file_info.filename) as file:
                            file_data = file.read()
                            file_obj = io.BytesIO(file_data)
                            file_obj.name = file_info.filename
                            uploaded_files.append(file_obj)
    
    if uploaded_files and st.button("Process Documents"):
        with st.spinner("Processing..."):
            documents, metadata = process_uploaded_files(uploaded_files)
            
            if documents:
                st.session_state.documents = documents
                st.session_state.metadata = metadata
                st.success(f"✅ Processed {len(documents)} documents!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Documents", len(documents))
                with col2:
                    total_words = sum(meta['word_count'] for meta in metadata)
                    st.metric("Total Words", f"{total_words:,}")
                with col3:
                    st.metric("Status", "Ready for Search")

elif page == "Search":
    st.markdown("## 🔍 Search Meeting Minutes")
    
    documents = st.session_state.documents
    metadata = st.session_state.metadata
    
    if not documents:
        st.warning("Please upload documents first in the Upload section.")
    else:
        query = st.text_input("Search query:", placeholder="e.g., project timeline, budget discussion...")
        top_k = st.selectbox("Results to show:", [5, 10, 15])
        
        if query and query.strip():
            with st.spinner("Searching..."):
                results = keyword_search(query, documents, metadata, top_k=top_k)
                
                if results:
                    st.markdown(f"### 📊 Found {len(results)} matches")
                    
                    for i, result in enumerate(results):
                        st.markdown(f"""
                        <div class="card">
                            <h3>📄 {result['metadata']['filename']}</h3>
                            <p><span class="match-score">Score: {result['score']:.2f}</span> • 
                            {result['metadata']['word_count']} words</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if result['matches']:
                            for match in result['matches']:
                                st.markdown(f"""
                                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                                    <p>{match['sentence']}</p>
                                    <small>Match: {match['similarity']:.2f}</small>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with st.expander("View full document"):
                            st.text_area("Content", result['document'], height=150, key=f"doc_{i}")
                        
                        st.markdown("---")
                else:
                    st.warning("No matches found. Try different search terms.")

elif page == "Analytics":
    st.markdown("## 📊 Analytics & Insights")
    
    metadata = st.session_state.metadata
    
    if not metadata:
        st.warning("Upload documents to see analytics.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", len(metadata))
        
        with col2:
            total_words = sum(meta['word_count'] for meta in metadata)
            st.metric("Total Words", f"{total_words:,}")
        
        with col3:
            avg_words = total_words // len(metadata)
            st.metric("Avg Words/Doc", f"{avg_words:,}")
        
        with col4:
            total_size = sum(meta['file_size'] for meta in metadata)
            st.metric("Total Size", f"{total_size / 1024:.1f} KB")
        
        st.markdown("### 📋 Document Details")
        for meta in metadata:
            with st.expander(f"{meta['filename']} ({meta['word_count']} words)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Uploaded:** {meta['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Size:** {meta['file_size']:,} bytes")
                with col2:
                    st.write(f"**Sentences:** {meta['sentence_count']}")
                    st.write(f"**Words:** {meta['word_count']}")