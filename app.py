import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

# Document processing
from docx import Document
import PyPDF2

# ML and search
from sentence_transformers import SentenceTransformer
import faiss
from sklearn.metrics.pairwise import cosine_similarity

# UI components
from streamlit_option_menu import option_menu

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
    .document-card {
        transition: transform 0.2s;
        cursor: pointer;
    }
    .document-card:hover {
        transform: translateY(-5px);
    }
    .search-box {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

class MeetingMinutesSearch:
    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []
        self.load_models()
    
    def load_models(self):
        """Load ML models for semantic search"""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            st.error(f"Error loading model: {e}")
    
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
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            st.error(f"Error reading DOCX: {e}")
            return ""
    
    def simple_text_analysis(self, text):
        """Perform basic text analysis without spaCy"""
        # Count words
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        
        # Count sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        # Find common keywords (top 10)
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
            # Read file content
            file_content = uploaded_file.getvalue()
            
            # Create a file-like object for processing
            file_obj = io.BytesIO(file_content)
            
            # Extract text based on file type
            text = ""
            if uploaded_file.name.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(file_obj)
            elif uploaded_file.name.lower().endswith('.docx'):
                text = self.extract_text_from_docx(file_obj)
            else:
                st.warning(f"Unsupported file type: {uploaded_file.name}")
                continue
            
            if text and text.strip():
                # Perform basic text analysis
                analysis = self.simple_text_analysis(text)
                
                metadata.append({
                    'filename': uploaded_file.name,
                    'upload_date': datetime.now(),
                    'file_size': len(file_content),
                    'word_count': analysis['word_count'],
                    'sentence_count': analysis['sentence_count'],
                    'common_words': analysis['common_words'],
                    'sentences': analysis['sentences'],
                    'content': text
                })
                documents.append(text)
            else:
                st.warning(f"Could not extract text from: {uploaded_file.name}")
        
        return documents, metadata
    
    def build_search_index(self, documents):
        """Build FAISS search index for semantic search"""
        if not documents:
            return None
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(documents)
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            index.add(embeddings)
            
            return index, embeddings
        except Exception as e:
            st.error(f"Error building search index: {e}")
            return None, None
    
    def semantic_search(self, query, top_k=5):
        """Perform semantic search with highlighting"""
        if self.index is None or not self.documents:
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    # Find relevant sentences using semantic similarity
                    document_text = self.documents[idx]
                    relevant_sentences = self.find_relevant_sentences_semantic(query, document_text)
                    
                    results.append({
                        'document': document_text,
                        'metadata': self.metadata[idx],
                        'score': float(score),
                        'matches': relevant_sentences
                    })
            
            return results
        except Exception as e:
            st.error(f"Search error: {e}")
            return []
    
    def find_relevant_sentences_semantic(self, query, document_text):
        """Find semantically relevant sentences using sentence embeddings"""
        try:
            # Split into sentences (simple approach)
            sentences = re.split(r'[.!?]+', document_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]  # Filter short sentences
            
            if not sentences:
                return []
            
            # Encode sentences and query
            sentence_embeddings = self.model.encode(sentences)
            query_embedding = self.model.encode([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, sentence_embeddings)[0]
            
            matches = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.3:  # Similarity threshold
                    matches.append({
                        'sentence': sentences[i],
                        'similarity': similarity,
                        'position': i
                    })
            
            return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:5]
        except Exception as e:
            return []
    
    def keyword_search(self, query, documents, metadata):
        """Fallback keyword search if semantic search fails"""
        results = []
        query_lower = query.lower()
        
        for i, (doc, meta) in enumerate(zip(documents, metadata)):
            # Simple keyword matching
            if query_lower in doc.lower():
                # Find sentences containing the keyword
                sentences = meta['sentences']
                keyword_sentences = []
                
                for j, sentence in enumerate(sentences):
                    if query_lower in sentence.lower():
                        keyword_sentences.append({
                            'sentence': sentence,
                            'similarity': 1.0,  # Exact match
                            'position': j
                        })
                
                results.append({
                    'document': doc,
                    'metadata': meta,
                    'score': 0.8,  # Default score for keyword matches
                    'matches': keyword_sentences[:5]  # Limit to 5 matches
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)

def main():
    # Initialize session state
    if 'search_engine' not in st.session_state:
        st.session_state.search_engine = MeetingMinutesSearch()
    if 'documents_processed' not in st.session_state:
        st.session_state.documents_processed = False
    
    search_engine = st.session_state.search_engine
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center;">
            <h1>🔍 MeetSearch Pro</h1>
            <p>AI-Powered Meeting Minutes Search</p>
        </div>
        """, unsafe_allow_html=True)
        
        selected = option_menu(
            menu_title="Navigation",
            options=["Dashboard", "Upload", "Search", "Analytics"],
            icons=["house", "cloud-upload", "search", "graph-up"],
            menu_icon="cast",
            default_index=0
        )
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        if search_engine.metadata:
            st.info(f"📊 Documents: {len(search_engine.metadata)}")
            total_words = sum(meta['word_count'] for meta in search_engine.metadata)
            st.success(f"📝 Total Words: {total_words:,}")

    # Main content based on selection
    if selected == "Dashboard":
        show_dashboard(search_engine)
    elif selected == "Upload":
        show_upload_section(search_engine)
    elif selected == "Search":
        show_search_section(search_engine)
    elif selected == "Analytics":
        show_analytics_section(search_engine)

def show_dashboard(search_engine):
    """Display the main dashboard"""
    st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🚀 Smart Semantic Search</h3>
            <p>Finds related concepts and meanings beyond exact keyword matching.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 AI-Powered Insights</h3>
            <p>Extract meaningful patterns and trends from your meetings.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>💾 Multi-Format Support</h3>
            <p>Upload PDF and Word documents individually or in ZIP folders.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick start guide
    st.markdown("---")
    st.markdown("## 🚀 Quick Start Guide")
    
    steps = [
        "1. **Upload** your meeting minutes (PDF/DOCX) in the Upload section",
        "2. **Search** for terms, concepts, or ideas in the Search section", 
        "3. **View** highlighted results with relevance scores",
        "4. **Analyze** patterns and insights in the Analytics section"
    ]
    
    for step in steps:
        st.markdown(step)
    
    # Feature highlights
    st.markdown("---")
    st.markdown("## ✨ Key Features")
    
    features = [
        "**Semantic Understanding**: Search for 'animals' and find mentions of 'pets', 'wildlife', 'zoo'",
        "**Multi-Format Support**: Upload PDF and Word documents with automatic text extraction",
        "**Relevance Scoring**: AI-powered ranking of results by semantic similarity",
        "**Contextual Highlighting**: See your search terms in context with highlighted matches",
        "**Advanced Analytics**: Get insights about your document collection and usage patterns"
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
            help="You can select multiple PDF or Word files"
        )
    else:
        zip_file = st.file_uploader(
            "Upload ZIP folder containing documents",
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
                            file_obj = io.BytesIO(file_data)
                            file_obj.name = file_info.filename
                            uploaded_files.append(file_obj)
    
    if uploaded_files and st.button("Process Documents", type="primary"):
        with st.spinner("Processing documents... This may take a moment."):
            documents, metadata = search_engine.process_uploaded_files(uploaded_files)
            
            if documents:
                search_engine.documents = documents
                search_engine.metadata = metadata
                
                # Build search index
                index, embeddings = search_engine.build_search_index(documents)
                if index is not None:
                    search_engine.index = index
                    st.session_state.documents_processed = True
                    st.success(f"✅ Successfully processed {len(documents)} documents!")
                else:
                    st.warning("⚠️ Search index could not be built, but documents are loaded for keyword search.")
                
                # Show summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Documents Processed", len(documents))
                with col2:
                    total_words = sum(meta['word_count'] for meta in metadata)
                    st.metric("Total Words", f"{total_words:,}")
                with col3:
                    avg_words = total_words // len(metadata) if metadata else 0
                    st.metric("Avg Words per Doc", f"{avg_words:,}")
                
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
                            st.write("**Common words:**")
                            for word, count in meta['common_words'][:3]:
                                st.write(f"  - {word} ({count})")
                        
                        st.write("**Preview:**")
                        preview = meta['content'][:400] + "..." if len(meta['content']) > 400 else meta['content']
                        st.text(preview)

def show_search_section(search_engine):
    """Handle search functionality"""
    st.markdown("## 🔍 Smart Search")
    
    if not search_engine.documents:
        st.warning("📁 Please upload some documents first to enable search.")
        st.info("Go to the Upload section to add your meeting minutes.")
        return
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Enter your search query:",
            placeholder="e.g., project timeline, budget discussion, action items, marketing strategy..."
        )
    
    with col2:
        top_k = st.selectbox("Results to show:", [5, 10, 15])
    
    # Search type options
    search_type = st.radio(
        "Search type:",
        ["Semantic Search (Recommended)", "Keyword Search"],
        horizontal=True
    )
    
    if query:
        with st.spinner("🔍 Searching through documents..."):
            if search_type == "Semantic Search (Recommended)" and search_engine.index is not None:
                results = search_engine.semantic_search(query, top_k=top_k)
            else:
                results = search_engine.keyword_search(query, search_engine.documents, search_engine.metadata)
            
            if results:
                st.markdown(f"### 📊 Found {len(results)} relevant documents")
                
                for i, result in enumerate(results):
                    # Document card
                    st.markdown(f"""
                    <div class="card document-card">
                        <h3>📄 {result['metadata']['filename']}</h3>
                        <p><span class="match-score">Relevance Score: {result['score']:.3f}</span> • 
                        {result['metadata']['word_count']} words • 
                        {result['metadata']['sentence_count']} sentences</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show top matches
                    if result['matches']:
                        st.markdown("**Top matches in this document:**")
                        for match in result['matches']:
                            # Highlight the query in context
                            display_text = match['sentence']
                            # Simple case-insensitive highlighting
                            query_words = query.lower().split()
                            for word in query_words:
                                if word in display_text.lower():
                                    display_text = re.sub(
                                        f'({re.escape(word)})', 
                                        r'<span class="highlight">\1</span>', 
                                        display_text, 
                                        flags=re.IGNORECASE
                                    )
                            
                            st.markdown(f"""
                            <div style="margin-left: 20px; margin-bottom: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                                <p>🔹 {display_text}</p>
                                <small>Similarity: {match['similarity']:.3f}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show full document content
                    with st.expander("📖 View full document content"):
                        st.text_area(
                            f"Content of {result['metadata']['filename']}",
                            result['document'],
                            height=200,
                            key=f"doc_{i}"
                        )
                    
                    st.markdown("---")
            else:
                st.warning("❌ No matches found. Try a different search term or more general query.")
                st.info("💡 Tip: Try searching for broader concepts or related terms.")

def show_analytics_section(search_engine):
    """Show analytics and insights"""
    st.markdown("## 📊 Analytics & Insights")
    
    if not search_engine.metadata:
        st.warning("📁 Upload documents to see analytics and insights.")
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
    
    # Word count distribution
    if len(search_engine.metadata) > 1:
        st.markdown("### 📊 Document Size Distribution")
        word_counts = [meta['word_count'] for meta in search_engine.metadata]
        
        import plotly.express as px
        fig = px.histogram(x=word_counts, nbins=10, title="Distribution of Document Word Counts")
        fig.update_layout(xaxis_title="Word Count", yaxis_title="Number of Documents")
        st.plotly_chart(fig)
    
    # Common words analysis
    st.markdown("### 🔤 Most Common Words")
    all_words = []
    for meta in search_engine.metadata:
        all_words.extend([word for word, count in meta['common_words']])
    
    if all_words:
        word_freq = Counter(all_words)
        common_words_df = pd.DataFrame(word_freq.most_common(20), columns=['Word', 'Frequency'])
        st.dataframe(common_words_df, use_container_width=True)
    
    # Document list
    st.markdown("### 📋 All Documents")
    for meta in search_engine.metadata:
        with st.expander(f"{meta['filename']} ({meta['word_count']} words)"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Uploaded:** {meta['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Size:** {meta['file_size']:,} bytes")
            with col2:
                st.write(f"**Sentences:** {meta['sentence_count']}")
                st.write(f"**Words:** {meta['word_count']}")
            
            st.write("**Top words:**")
            for word, count in meta['common_words'][:5]:
                st.write(f"- {word} ({count})")

if __name__ == "__main__":
    main()