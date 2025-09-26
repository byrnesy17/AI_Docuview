import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

# Document processing
from docx import Document
import PyPDF2

# Configure the page
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

class MeetingMinutesSearch:
    def __init__(self):
        self.model = None
        self.documents = []
        self.metadata = []
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'documents_processed' not in st.session_state:
            st.session_state.documents_processed = False
        if 'search_index' not in st.session_state:
            st.session_state.search_index = None
    
    def load_models(self):
        """Try to load ML models with fallback"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            return True
        except Exception as e:
            st.warning(f"AI model not available: {e}")
            self.model = None
            return False
    
    def extract_text_from_pdf(self, file):
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
    
    def extract_text_from_docx(self, file):
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
    
    def simple_text_analysis(self, text):
        """Perform basic text analysis"""
        # Count words
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        
        # Count sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        # Find common keywords
        word_freq = Counter(words)
        common_words = word_freq.most_common(10)
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'common_words': common_words,
            'sentences': sentences
        }
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and extract text"""
        documents = []
        metadata = []
        
        for uploaded_file in uploaded_files:
            # Extract text based on file type
            text = ""
            if uploaded_file.name.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(uploaded_file)
            elif uploaded_file.name.lower().endswith('.docx'):
                text = self.extract_text_from_docx(uploaded_file)
            else:
                continue
            
            if text and text.strip():
                # Perform basic text analysis
                analysis = self.simple_text_analysis(text)
                
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
    
    def keyword_search(self, query, top_k=5):
        """Keyword search with basic matching"""
        if not self.documents:
            return []
        
        results = []
        query_lower = query.lower()
        query_words = query_lower.split()
        
        for i, (doc, meta) in enumerate(zip(self.documents, self.metadata)):
            doc_lower = doc.lower()
            match_score = 0
            keyword_sentences = []
            
            # Check each sentence for matches
            for j, sentence in enumerate(meta['sentences']):
                sentence_lower = sentence.lower()
                sentence_score = 0
                highlighted_sentence = sentence
                
                for word in query_words:
                    if word in sentence_lower:
                        sentence_score += 1
                        # Highlight the word
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
                normalized_score = min(match_score / (len(query_words) * 5), 1.0)
                results.append({
                    'document': doc,
                    'metadata': meta,
                    'score': normalized_score,
                    'matches': keyword_sentences[:3]  # Limit matches
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]

def main():
    # Initialize search engine
    if 'search_engine' not in st.session_state:
        st.session_state.search_engine = MeetingMinutesSearch()
    
    search_engine = st.session_state.search_engine
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center;">
            <h1>🔍 MeetSearch Pro</h1>
            <p>AI-Powered Meeting Minutes Search</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple navigation without external dependencies
        page = st.radio(
            "Navigation",
            ["Dashboard", "Upload Documents", "Search", "Analytics"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        if search_engine.metadata:
            st.info(f"📊 Documents: {len(search_engine.metadata)}")
            total_words = sum(meta['word_count'] for meta in search_engine.metadata)
            st.success(f"📝 Total Words: {total_words:,}")
    
    # Page routing
    if page == "Dashboard":
        show_dashboard(search_engine)
    elif page == "Upload Documents":
        show_upload_section(search_engine)
    elif page == "Search":
        show_search_section(search_engine)
    elif page == "Analytics":
        show_analytics_section(search_engine)

def show_dashboard(search_engine):
    """Display the main dashboard"""
    st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🚀 Smart Search</h3>
            <p>Find exactly what you're looking for in your meeting minutes.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 Document Insights</h3>
            <p>Gain valuable insights from your meeting data.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>💾 Multi-Format</h3>
            <p>Support for PDF and Word documents.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick start guide
    st.markdown("---")
    st.markdown("## 🚀 Get Started in 3 Steps")
    
    steps = [
        "1. **Upload** your meeting minutes (PDF or Word documents)",
        "2. **Search** for specific terms or phrases", 
        "3. **View** highlighted results with context"
    ]
    
    for step in steps:
        st.markdown(step)
    
    # Feature highlights
    st.markdown("---")
    st.markdown("## ✨ Key Features")
    
    features = [
        "**Keyword Search**: Find exact matches with highlighting",
        "**Multi-Document Support**: Search across all uploaded files",
        "**Document Analytics**: View statistics and insights",
        "**Modern Interface**: Clean, professional design",
        "**Easy Upload**: Drag and drop or select multiple files"
    ]
    
    for feature in features:
        st.markdown(f"✅ {feature}")

def show_upload_section(search_engine):
    """Handle document uploads"""
    st.markdown("## 📤 Upload Meeting Minutes")
    
    # Upload options
    upload_option = st.radio(
        "Choose upload method:",
        ["Single Files", "ZIP Folder"],
        horizontal=True
    )
    
    uploaded_files = []
    
    if upload_option == "Single Files":
        uploaded_files = st.file_uploader(
            "Upload PDF or Word documents",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Select multiple PDF or Word files"
        )
    else:
        zip_file = st.file_uploader(
            "Upload ZIP folder",
            type=['zip'],
            help="ZIP file containing PDF or Word documents"
        )
        
        if zip_file:
            with zipfile.ZipFile(zip_file, 'r') as z:
                for file_info in z.infolist():
                    if file_info.filename.lower().endswith(('.pdf', '.docx')):
                        with z.open(file_info.filename) as file:
                            file_data = file.read()
                            # Create a file-like object
                            from io import BytesIO
                            file_obj = BytesIO(file_data)
                            file_obj.name = file_info.filename
                            uploaded_files.append(file_obj)
    
    if uploaded_files and st.button("Process Documents", type="primary"):
        with st.spinner("Processing documents..."):
            documents, metadata = search_engine.process_uploaded_files(uploaded_files)
            
            if documents:
                search_engine.documents = documents
                search_engine.metadata = metadata
                st.session_state.documents_processed = True
                
                st.success(f"✅ Successfully processed {len(documents)} documents!")
                
                # Show summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Documents Processed", len(documents))
                with col2:
                    total_words = sum(meta['word_count'] for meta in metadata)
                    st.metric("Total Words", f"{total_words:,}")
                with col3:
                    avg_words = total_words // len(metadata) if metadata else 0
                    st.metric("Avg Words/Doc", f"{avg_words:,}")
                
                # Show document preview
                st.markdown("### 📋 Document Preview")
                for i, meta in enumerate(metadata[:3]):  # Show first 3
                    with st.expander(f"📄 {meta['filename']} ({meta['word_count']} words)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Size:** {meta['file_size']:,} bytes")
                            st.write(f"**Sentences:** {meta['sentence_count']}")
                        with col2:
                            st.write(f"**Uploaded:** {meta['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                        
                        st.write("**Preview:**")
                        preview = meta['content'][:300] + "..." if len(meta['content']) > 300 else meta['content']
                        st.text(preview)

def show_search_section(search_engine):
    """Handle search functionality"""
    st.markdown("## 🔍 Search Meeting Minutes")
    
    if not search_engine.documents:
        st.warning("📁 Please upload documents first in the Upload section.")
        st.info("Go to 'Upload Documents' to add your meeting minutes.")
        return
    
    # Search interface
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., project timeline, budget, action items, decisions..."
    )
    
    top_k = st.selectbox("Number of results:", [5, 10, 15])
    
    if query:
        with st.spinner("Searching through documents..."):
            results = search_engine.keyword_search(query, top_k=top_k)
            
            if results:
                st.markdown(f"### 📊 Found {len(results)} matches")
                
                for i, result in enumerate(results):
                    # Document header
                    st.markdown(f"""
                    <div class="card">
                        <h3>📄 {result['metadata']['filename']}</h3>
                        <p><span class="match-score">Relevance: {result['score']:.2f}</span> • 
                        {result['metadata']['word_count']} words • 
                        {result['metadata']['sentence_count']} sentences</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show matches
                    if result['matches']:
                        st.markdown("**Matching sentences:**")
                        for match in result['matches']:
                            st.markdown(f"""
                            <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                                <p>{match['sentence']}</p>
                                <small>Match strength: {match['similarity']:.2f}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show full document on expand
                    with st.expander("View full document content"):
                        st.text_area(
                            "Document content:",
                            result['document'],
                            height=150,
                            key=f"doc_{i}"
                        )
                    
                    st.markdown("---")
            else:
                st.warning("No matches found. Try different search terms.")
                st.info("💡 Tip: Use specific keywords or try shorter phrases.")

def show_analytics_section(search_engine):
    """Show analytics and insights"""
    st.markdown("## 📊 Analytics & Insights")
    
    if not search_engine.metadata:
        st.warning("Upload documents to see analytics.")
        return
    
    # Basic statistics
    st.markdown("### 📈 Document Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", len(search_engine.metadata))
    
    with col2:
        total_words = sum(meta['word_count'] for meta in search_engine.metadata)
        st.metric("Total Words", f"{total_words:,}")
    
    with col3:
        avg_words = total_words // len(search_engine.metadata)
        st.metric("Avg Words/Doc", f"{avg_words:,}")
    
    with col4:
        total_size = sum(meta['file_size'] for meta in search_engine.metadata)
        st.metric("Total Size", f"{total_size / 1024:.1f} KB")
    
    # Common words analysis
    st.markdown("### 🔤 Most Common Words")
    all_words = []
    for meta in search_engine.metadata:
        all_words.extend([word for word, count in meta['common_words']])
    
    if all_words:
        word_freq = Counter(all_words)
        common_words = word_freq.most_common(15)
        
        # Display as a table
        words_df = pd.DataFrame(common_words, columns=['Word', 'Frequency'])
        st.dataframe(words_df, use_container_width=True)
    
    # Document list
    st.markdown("### 📋 Document Details")
    for meta in search_engine.metadata:
        with st.expander(f"{meta['filename']} ({meta['word_count']} words)"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Uploaded:** {meta['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Size:** {meta['file_size']:,} bytes")
            with col2:
                st.write(f"**Sentences:** {meta['sentence_count']}")
                st.write(f"**Words:** {meta['word_count']}")
            
            st.write("**Top 5 words:**")
            for word, count in meta['common_words'][:5]:
                st.write(f"- {word} ({count})")

if __name__ == "__main__":
    main()