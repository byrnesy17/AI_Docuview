import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import io
from datetime import datetime
import re
from collections import Counter
import sys

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
        """Load ML models for semantic search with fallback"""
        try:
            # Try to import with compatibility handling
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            st.success("✅ AI model loaded successfully!")
        except ImportError as e:
            st.warning(f"⚠️ Advanced AI features disabled: {e}")
            self.model = None
        except Exception as e:
            st.warning(f"⚠️ Could not load AI model: {e}")
            self.model = None
    
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
        """Perform basic text analysis"""
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
        """Build search index for semantic search with fallback"""
        if not documents or self.model is None:
            return None
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(documents)
            
            # Try to import FAISS, with fallback
            try:
                import faiss
                # Create FAISS index
                dimension = embeddings.shape[1]
                index = faiss.IndexFlatIP(dimension)
                
                # Normalize embeddings for cosine similarity
                faiss.normalize_L2(embeddings)
                index.add(embeddings)
                
                return index, embeddings
            except ImportError:
                st.warning("FAISS not available, using simple similarity search")
                return None, embeddings
                
        except Exception as e:
            st.error(f"Error building search index: {e}")
            return None, None
    
    def semantic_search(self, query, top_k=5):
        """Perform semantic search with fallback to keyword search"""
        if not self.documents:
            return []
        
        # Try semantic search if model is available
        if self.model is not None and self.index is not None:
            try:
                return self._semantic_search_with_faiss(query, top_k)
            except Exception as e:
                st.warning(f"Semantic search failed, using keyword search: {e}")
        
        # Fallback to keyword search
        return self.keyword_search(query, self.documents, self.metadata, top_k)
    
    def _semantic_search_with_faiss(self, query, top_k):
        """Internal method for FAISS-based semantic search"""
        # Encode query
        query_embedding = self.model.encode([query])
        
        try:
            import faiss
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    results.append({
                        'document': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'score': float(score),
                        'matches': self._find_semantic_matches(query, self.documents[idx])
                    })
            
            return results
        except:
            # Fallback to simple similarity search
            return self._semantic_search_simple(query, top_k)
    
    def _semantic_search_simple(self, query, top_k):
        """Simple semantic search without FAISS"""
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_embedding = self.model.encode([query])
        doc_embeddings = self.model.encode(self.documents)
        
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'score': float(similarities[idx]),
                    'matches': self._find_semantic_matches(query, self.documents[idx])
                })
        
        return results
    
    def _find_semantic_matches(self, query, document_text):
        """Find semantically relevant sentences"""
        if self.model is None:
            return []
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Split into sentences
            sentences = re.split(r'[.!?]+', document_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if not sentences:
                return []
            
            # Encode sentences and query
            sentence_embeddings = self.model.encode(sentences)
            query_embedding = self.model.encode([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, sentence_embeddings)[0]
            
            matches = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.3:
                    matches.append({
                        'sentence': sentences[i],
                        'similarity': similarity,
                        'position': i
                    })
            
            return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:3]
        except:
            return []
    
    def keyword_search(self, query, documents, metadata, top_k=5):
        """Keyword search with basic matching"""
        results = []
        query_lower = query.lower()
        query_words = query_lower.split()
        
        for i, (doc, meta) in enumerate(zip(documents, metadata)):
            doc_lower = doc.lower()
            
            # Calculate match score based on word presence
            match_score = 0
            keyword_sentences = []
            
            for j, sentence in enumerate(meta['sentences']):
                sentence_lower = sentence.lower()
                sentence_score = 0
                
                for word in query_words:
                    if word in sentence_lower:
                        sentence_score += 1
                        # Highlight all occurrences
                        highlighted = re.sub(
                            f'({re.escape(word)})', 
                            r'<span class="highlight">\1</span>', 
                            sentence, 
                            flags=re.IGNORECASE
                        )
                        
                        keyword_sentences.append({
                            'sentence': highlighted,
                            'similarity': sentence_score / len(query_words),
                            'position': j
                        })
                
                match_score += sentence_score
            
            if match_score > 0:
                # Normalize score
                normalized_score = min(match_score / (len(query_words) * 10), 1.0)
                
                results.append({
                    'document': doc,
                    'metadata': meta,
                    'score': normalized_score,
                    'matches': keyword_sentences[:5]  # Limit matches
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]

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
        
        from streamlit_option_menu import option_menu
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
        
        # Model status
        st.markdown("### AI Status")
        if search_engine.model is not None:
            st.success("✅ Semantic Search Enabled")
        else:
            st.warning("⚠️ Keyword Search Only")

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
            <h3>🚀 Smart Search</h3>
            <p>Advanced search that understands context and meaning.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 Document Insights</h3>
            <p>Extract meaningful patterns from your meetings.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>💾 Multi-Format</h3>
            <p>Upload PDF and Word documents with ease.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature status
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Current Features")
        features = [
            "✅ PDF and Word document support",
            "✅ ZIP folder uploads",
            "✅ Keyword search with highlighting",
            "✅ Document analytics and insights",
            "✅ Modern, responsive UI"
        ]
        
        for feature in features:
            st.markdown(feature)
    
    with col2:
        st.markdown("### 🤖 AI Features")
        ai_features = [
            "🔍 Semantic search understanding",
            "📊 Relevance scoring",
            "💡 Contextual matching"
        ]
        
        if search_engine.model is not None:
            ai_features = [f.replace("🔍", "✅") for f in ai_features]
        else:
            ai_features = [f.replace("🔍", "⚠️") for f in ai_features]
            st.info("AI features will be enabled automatically when models load")
        
        for feature in ai_features:
            st.markdown(feature)

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
                            file_obj = io.BytesIO(file_data)
                            file_obj.name = file_info.filename
                            uploaded_files.append(file_obj)
    
    if uploaded_files and st.button("Process Documents", type="primary"):
        with st.spinner("Processing documents..."):
            documents, metadata = search_engine.process_uploaded_files(uploaded_files)
            
            if documents:
                search_engine.documents = documents
                search_engine.metadata = metadata
                
                # Build search index
                index, embeddings = search_engine.build_search_index(documents)
                search_engine.index = index
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
                    if search_engine.model is not None:
                        st.metric("Search Mode", "AI Semantic")
                    else:
                        st.metric("Search Mode", "Keyword")

def show_search_section(search_engine):
    """Handle search functionality"""
    st.markdown("## 🔍 Search Meeting Minutes")
    
    if not search_engine.documents:
        st.warning("📁 Please upload documents first in the Upload section.")
        return
    
    # Search interface
    query = st.text_input(
        "Search for words, phrases, or concepts:",
        placeholder="e.g., project timeline, budget discussion, action items..."
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        top_k = st.selectbox("Results to show:", [5, 10, 15])
    with col2:
        if search_engine.model is not None:
            st.info("🤖 AI Semantic Search Active")
        else:
            st.warning("🔤 Keyword Search Active")
    
    if query:
        with st.spinner("Searching..."):
            results = search_engine.semantic_search(query, top_k=top_k)
            
            if results:
                st.markdown(f"### 📊 Found {len(results)} matches")
                
                for i, result in enumerate(results):
                    # Document card
                    st.markdown(f"""
                    <div class="card">
                        <h3>📄 {result['metadata']['filename']}</h3>
                        <p><span class="match-score">Relevance: {result['score']:.3f}</span> • 
                        {result['metadata']['word_count']} words</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show matches
                    if result['matches']:
                        for match in result['matches']:
                            st.markdown(f"""
                            <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                                <p>{match['sentence']}</p>
                                <small>Similarity: {match['similarity']:.3f}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with st.expander("View full document"):
                        st.text_area("Content", result['document'], height=150, key=f"doc_{i}")
                    
                    st.markdown("---")
            else:
                st.warning("No matches found. Try different search terms.")

def show_analytics_section(search_engine):
    """Show analytics and insights"""
    st.markdown("## 📊 Analytics")
    
    if not search_engine.metadata:
        st.warning("Upload documents to see analytics.")
        return
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Documents", len(search_engine.metadata))
    with col2:
        total_words = sum(meta['word_count'] for meta in search_engine.metadata)
        st.metric("Total Words", f"{total_words:,}")
    with col3:
        avg_words = total_words // len(search_engine.metadata)
        st.metric("Avg Words/Doc", f"{avg_words:,}")
    
    # Document list
    st.markdown("### 📋 Documents")
    for meta in search_engine.metadata:
        with st.expander(f"{meta['filename']} ({meta['word_count']} words)"):
            st.write(f"**Size:** {meta['file_size']:,} bytes")
            st.write(f"**Sentences:** {meta['sentence_count']}")
            st.write("**Common words:**")
            for word, count in meta['common_words'][:5]:
                st.write(f"- {word} ({count})")

if __name__ == "__main__":
    main()