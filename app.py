import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
import zipfile
import io
from datetime import datetime
import base64
from PIL import Image
import plotly.express as px

# Document processing
from docx import Document
import PyPDF2
import spacy

# ML and search
from sentence_transformers import SentenceTransformer
import faiss
from sklearn.metrics.pairwise import cosine_similarity

# UI components
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

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
</style>
""", unsafe_allow_html=True)

class MeetingMinutesSearch:
    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []
        self.nlp = None
        self.load_models()
    
    def load_models(self):
        """Load ML models for semantic search"""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.nlp = spacy.load("en_core_web_sm")
        except:
            st.warning("Some models need to be downloaded. This might take a moment...")
            try:
                os.system("python -m spacy download en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            except:
                st.error("Failed to load required models. Please check the installation.")
    
    def extract_text_from_pdf(self, file):
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
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
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and extract text"""
        documents = []
        metadata = []
        
        for uploaded_file in uploaded_files:
            # Read file content
            file_content = uploaded_file.read()
            
            # Create a file-like object for processing
            file_obj = io.BytesIO(file_content)
            
            # Extract text based on file type
            if uploaded_file.name.endswith('.pdf'):
                text = self.extract_text_from_pdf(file_obj)
            elif uploaded_file.name.endswith('.docx'):
                text = self.extract_text_from_docx(file_obj)
            else:
                continue  # Skip unsupported files
            
            if text.strip():
                # Extract key information using spaCy
                doc = self.nlp(text)
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                sentences = [sent.text for sent in doc.sents]
                
                metadata.append({
                    'filename': uploaded_file.name,
                    'upload_date': datetime.now(),
                    'file_size': len(file_content),
                    'entities': entities,
                    'sentences': sentences,
                    'content': text
                })
                documents.append(text)
        
        return documents, metadata
    
    def build_search_index(self, documents):
        """Build FAISS search index for semantic search"""
        if not documents:
            return None
        
        # Generate embeddings
        embeddings = self.model.encode(documents)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product index for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        return index, embeddings
    
    def semantic_search(self, query, top_k=5):
        """Perform semantic search with highlighting"""
        if self.index is None or not self.documents:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'score': float(score),
                    'matches': self.find_semantic_matches(query, self.documents[idx])
                })
        
        return results
    
    def find_semantic_matches(self, query, document):
        """Find semantic matches within a document"""
        doc_sentences = [sent.text for sent in self.nlp(document).sents]
        sentence_embeddings = self.model.encode(doc_sentences)
        query_embedding = self.model.encode([query])
        
        similarities = cosine_similarity(query_embedding, sentence_embeddings)[0]
        matches = []
        
        for i, similarity in enumerate(similarities):
            if similarity > 0.3:  # Threshold for semantic similarity
                matches.append({
                    'sentence': doc_sentences[i],
                    'similarity': similarity,
                    'position': i
                })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)

def main():
    # Initialize session state
    if 'search_engine' not in st.session_state:
        st.session_state.search_engine = MeetingMinutesSearch()
    if 'documents_processed' not in st.session_state:
        st.session_state.documents_processed = False
    
    search_engine = st.session_state.search_engine
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1f77b4/ffffff?text=MeetSearch+Pro", use_column_width=True)
        
        selected = option_menu(
            menu_title="Navigation",
            options=["Dashboard", "Upload", "Search", "Analytics", "Settings"],
            icons=["house", "cloud-upload", "search", "graph-up", "gear"],
            menu_icon="cast",
            default_index=0
        )
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        if search_engine.metadata:
            st.info(f"📊 Documents: {len(search_engine.metadata)}")
            st.success(f"🔍 Searchable: {len(search_engine.documents)}")
    
    # Main content area
    if selected == "Dashboard":
        show_dashboard(search_engine)
    elif selected == "Upload":
        show_upload_section(search_engine)
    elif selected == "Search":
        show_search_section(search_engine)
    elif selected == "Analytics":
        show_analytics_section(search_engine)
    elif selected == "Settings":
        show_settings_section(search_engine)

def show_dashboard(search_engine):
    """Display the main dashboard"""
    st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🚀 Smart Search</h3>
            <p>Semantic search that understands context and meaning beyond exact keywords.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 Advanced Analytics</h3>
            <p>Gain insights from your meeting data with visual analytics and trends.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>💾 Multi-Format Support</h3>
            <p>Upload PDF, Word documents, or ZIP folders containing multiple files.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("---")
    st.markdown("### Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Upload Documents", use_container_width=True):
            st.experimental_set_query_params(page="Upload")
    
    with col2:
        if st.button("🔍 Start Searching", use_container_width=True):
            st.experimental_set_query_params(page="Search")
    
    with col3:
        if st.button("📊 View Analytics", use_container_width=True):
            st.experimental_set_query_params(page="Analytics")

def show_upload_section(search_engine):
    """Handle document uploads"""
    st.markdown("## 📤 Upload Meeting Minutes")
    
    # Upload options
    upload_option = st.radio(
        "Choose upload method:",
        ["Single Files", "ZIP Folder"],
        horizontal=True
    )
    
    if upload_option == "Single Files":
        uploaded_files = st.file_uploader(
            "Upload PDF or Word documents",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="You can select multiple files"
        )
    else:
        zip_file = st.file_uploader(
            "Upload ZIP folder containing documents",
            type=['zip'],
            help="ZIP file containing PDF or Word documents"
        )
        uploaded_files = []
        if zip_file:
            with zipfile.ZipFile(zip_file, 'r') as z:
                for file_info in z.infolist():
                    if file_info.filename.endswith(('.pdf', '.docx')):
                        file_data = z.read(file_info.filename)
                        uploaded_files.append(io.BytesIO(file_data))
    
    if uploaded_files:
        with st.spinner("Processing documents..."):
            documents, metadata = search_engine.process_uploaded_files(uploaded_files)
            
            if documents:
                search_engine.documents = documents
                search_engine.metadata = metadata
                search_engine.index, _ = search_engine.build_search_index(documents)
                st.session_state.documents_processed = True
                
                st.success(f"✅ Successfully processed {len(documents)} documents!")
                
                # Show document preview
                st.markdown("### 📋 Document Preview")
                for meta in metadata[:3]:  # Show first 3 documents
                    with st.expander(f"📄 {meta['filename']}"):
                        st.write(f"**Size:** {meta['file_size']} bytes")
                        st.write(f"**Entities found:** {len(meta['entities'])}")
                        st.write("**Preview:**")
                        st.text(meta['content'][:500] + "..." if len(meta['content']) > 500 else meta['content'])

def show_search_section(search_engine):
    """Handle search functionality"""
    st.markdown("## 🔍 Semantic Search")
    
    if not search_engine.documents:
        st.warning("Please upload some documents first to enable search.")
        return
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Enter your search query:",
            placeholder="e.g., project timeline, budget discussion, action items..."
        )
    
    with col2:
        top_k = st.selectbox("Results to show:", [5, 10, 15, 20])
    
    # Advanced options
    with st.expander("🔧 Advanced Search Options"):
        col1, col2 = st.columns(2)
        with col1:
            semantic_threshold = st.slider("Semantic similarity threshold", 0.1, 0.9, 0.3)
        with col2:
            date_filter = st.date_input("Filter by date range")
    
    if query:
        with st.spinner("Searching..."):
            results = search_engine.semantic_search(query, top_k=top_k)
            
            if results:
                st.markdown(f"### 📊 Found {len(results)} matches")
                
                for i, result in enumerate(results):
                    with st.container():
                        st.markdown(f"""
                        <div class="card document-card">
                            <h3>📄 {result['metadata']['filename']}</h3>
                            <p><span class="match-score">Relevance: {result['score']:.3f}</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show matches
                        for match in result['matches'][:3]:  # Show top 3 matches per document
                            highlighted_text = match['sentence'].replace(
                                query, f'<span class="highlight">{query}</span>'
                            )
                            
                            st.markdown(f"""
                            <div style="margin-left: 20px; margin-bottom: 10px;">
                                <p>🔹 {highlighted_text}</p>
                                <small>Similarity: {match['similarity']:.3f}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Show full document on expand
                        with st.expander("View full document"):
                            st.text_area(
                                "Document content:",
                                result['document'],
                                height=200,
                                key=f"doc_{i}"
                            )
            else:
                st.warning("No matches found. Try a different search term.")

def show_analytics_section(search_engine):
    """Show analytics and insights"""
    st.markdown("## 📊 Analytics & Insights")
    
    if not search_engine.metadata:
        st.warning("Upload documents to see analytics.")
        return
    
    # Basic statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", len(search_engine.metadata))
    
    with col2:
        total_size = sum(meta['file_size'] for meta in search_engine.metadata)
        st.metric("Total Size", f"{total_size / 1024:.1f} KB")
    
    with col3:
        avg_entities = np.mean([len(meta['entities']) for meta in search_engine.metadata])
        st.metric("Avg Entities", f"{avg_entities:.1f}")
    
    with col4:
        recent_upload = max(meta['upload_date'] for meta in search_engine.metadata)
        st.metric("Last Upload", recent_upload.strftime("%m/%d"))
    
    # Entity analysis
    st.markdown("### 🏷️ Entity Analysis")
    all_entities = []
    for meta in search_engine.metadata:
        all_entities.extend([ent[1] for ent in meta['entities']])
    
    if all_entities:
        entity_counts = pd.Series(all_entities).value_counts()
        fig = px.pie(values=entity_counts.values, names=entity_counts.index, title="Entity Types Distribution")
        st.plotly_chart(fig)
    
    # Document timeline
    st.markdown("### 📅 Upload Timeline")
    upload_dates = [meta['upload_date'] for meta in search_engine.metadata]
    if upload_dates:
        date_counts = pd.Series(upload_dates).dt.date.value_counts().sort_index()
        fig = px.line(x=date_counts.index, y=date_counts.values, title="Documents Uploaded Over Time")
        st.plotly_chart(fig)

def show_settings_section(search_engine):
    """Application settings"""
    st.markdown("## ⚙️ Settings")
    
    st.markdown("### Search Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Default results per page", min_value=5, max_value=50, value=10)
        st.checkbox("Enable fuzzy matching", value=True)
    
    with col2:
        st.slider("Minimum similarity score", 0.1, 0.9, 0.3)
        st.checkbox("Show preview snippets", value=True)
    
    st.markdown("### Application")
    if st.button("Clear All Documents"):
        search_engine.documents = []
        search_engine.metadata = []
        search_engine.index = None
        st.session_state.documents_processed = False
        st.success("All documents cleared!")
    
    st.markdown("### About")
    st.info("""
    **MeetSearch Pro** v1.0  
    Advanced semantic search for meeting minutes.  
    Built with Streamlit, Transformers, and FAISS.
    """)

if __name__ == "__main__":
    main()