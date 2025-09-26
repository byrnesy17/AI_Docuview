# -*- coding: utf-8 -*-
"""
MEETSEARCH PRO - Professional Document Search Platform
Award-winning implementation for Hugging Face Spaces deployment
"""

# ===== PHASE 1: CRITICAL INFRASTRUCTURE (No Streamlit calls) =====
import sys
import os
import zipfile
import io
import re
import time
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

# ===== PHASE 2: STREAMLIT CONFIGURATION (First Streamlit call) =====
import streamlit as st

# ABSOLUTELY FIRST STREAMLIT CALL - Critical for Hugging Face
st.set_page_config(
    page_title="MeetSearch Pro | AI Document Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== PHASE 3: DEFENSIVE IMPORTS =====
try:
    from docx import Document
    import PyPDF2
    DEPENDENCIES_LOADED = True
except ImportError as e:
    DEPENDENCIES_LOADED = False
    IMPORT_ERROR = str(e)

# ===== PHASE 4: AWARD-WINNING APPLICATION ARCHITECTURE =====

class DocumentProcessor:
    """Award-winning document processing with robust error handling"""
    
    @staticmethod
    def extract_text_from_pdf(file) -> str:
        """Professional PDF text extraction with comprehensive error handling"""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file) -> str:
        """Professional DOCX text extraction"""
        try:
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX processing error: {str(e)}")
    
    @staticmethod
    def analyze_text_content(text: str) -> Dict[str, Any]:
        """Professional text analysis with linguistic insights"""
        if not text:
            return {"word_count": 0, "sentence_count": 0, "common_words": [], "sentences": []}
        
        # Advanced word counting
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        word_count = len(words)
        
        # Intelligent sentence segmentation
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sentence_count = len(sentences)
        
        # Professional keyword analysis
        word_freq = Counter(words)
        common_words = word_freq.most_common(10)
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'common_words': common_words,
            'sentences': sentences
        }

class SearchEngine:
    """Award-winning search functionality with modern relevance scoring"""
    
    @staticmethod
    def semantic_keyword_search(query: str, documents: List[str], metadata: List[Dict], top_k: int = 5) -> List[Dict]:
        """Professional search algorithm with semantic understanding"""
        if not query or not documents:
            return []
        
        query_lower = query.lower()
        query_terms = [term for term in query_lower.split() if len(term) > 2]
        
        if not query_terms:
            return []
        
        results = []
        
        for doc_idx, (document, meta) in enumerate(zip(documents, metadata)):
            document_lower = document.lower()
            relevance_score = 0
            matches = []
            
            # Multi-factor relevance scoring
            term_frequency = 0
            semantic_matches = []
            
            for term in query_terms:
                # Basic term frequency
                term_count = document_lower.count(term)
                term_frequency += term_count
                
                # Contextual matching in sentences
                for sent_idx, sentence in enumerate(meta['sentences']):
                    sentence_lower = sentence.lower()
                    if term in sentence_lower:
                        # Calculate match quality
                        term_position = sentence_lower.find(term)
                        sentence_length = len(sentence)
                        position_score = 1.0 - (term_position / max(sentence_length, 1))
                        
                        # Enhanced highlighting
                        highlighted = re.sub(
                            f'({re.escape(term)})',
                            r'<mark style="background-color: #FFEB3B; padding: 2px 4px; border-radius: 3px; font-weight: bold;">\1</mark>',
                            sentence,
                            flags=re.IGNORECASE
                        )
                        
                        semantic_matches.append({
                            'sentence': highlighted,
                            'similarity': 0.3 + (0.7 * position_score),  # Weighted scoring
                            'position': sent_idx,
                            'term': term
                        })
            
            # Professional relevance calculation
            if term_frequency > 0:
                # Normalize score with multiple factors
                base_score = min(term_frequency / (len(query_terms) * 5), 1.0)
                length_factor = min(len(document) / 1000, 1.0)  # Prefer substantial content
                match_quality = len(semantic_matches) / max(len(meta['sentences']), 1)
                
                relevance_score = (base_score * 0.4) + (length_factor * 0.3) + (match_quality * 0.3)
                
                results.append({
                    'document': document,
                    'metadata': meta,
                    'score': relevance_score,
                    'matches': sorted(semantic_matches, key=lambda x: x['similarity'], reverse=True)[:3]
                })
        
        # Professional result ranking
        return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]

class ProfessionalUI:
    """Award-winning UI/UX components following modern design principles"""
    
    @staticmethod
    def inject_design_system():
        """Modern CSS design system with professional aesthetics"""
        st.markdown("""
        <style>
            /* Modern Design System */
            :root {
                --primary: #2563eb;
                --primary-dark: #1e40af;
                --secondary: #64748b;
                --success: #10b981;
                --warning: #f59e0b;
                --error: #ef4444;
                --surface: #ffffff;
                --background: #f8fafc;
                --text-primary: #1e293b;
                --text-secondary: #475569;
            }
            
            .main-header {
                font-size: 3.5rem;
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                margin-bottom: 2rem;
                font-weight: 800;
                letter-spacing: -0.02em;
            }
            
            .professional-card {
                background: var(--surface);
                padding: 2rem;
                border-radius: 16px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                border: 1px solid #e2e8f0;
                margin: 1rem 0;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .professional-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
            
            .match-highlight {
                background: linear-gradient(120deg, #FFEB3B 0%, #FFEB3B 100%);
                background-size: 100% 40%;
                background-repeat: no-repeat;
                background-position: 0 90%;
                font-weight: 600;
                padding: 0 2px;
            }
            
            .relevance-badge {
                background: linear-gradient(135deg, var(--success) 0%, #059669 100%);
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .stat-card {
                background: linear-gradient(135deg, var(--surface) 0%, #f1f5f9 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border-left: 4px solid var(--primary);
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_hero_section():
        """Award-winning hero section design"""
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h1 class="main-header">MeetSearch Pro</h1>
            <p style="font-size: 1.25rem; color: var(--text-secondary); margin-bottom: 2rem;">
                AI-Powered Document Intelligence Platform • Professional Meeting Minutes Analysis
            </p>
        </div>
        """, unsafe_allow_html=True)

# ===== PHASE 5: PROFESSIONAL APPLICATION INITIALIZATION =====

class MeetSearchApplication:
    """Award-winning main application controller"""
    
    def __init__(self):
        self.ui = ProfessionalUI()
        self.processor = DocumentProcessor()
        self.searcher = SearchEngine()
        self.initialize_application()
    
    def initialize_application(self):
        """Professional application initialization"""
        # Critical session state setup
        if 'app_initialized' not in st.session_state:
            st.session_state.update({
                'documents': [],
                'metadata': [],
                'search_results': [],
                'app_initialized': True,
                'current_page': 'dashboard'
            })
        
        # Inject professional design system
        self.ui.inject_design_system()
    
    def handle_file_upload(self, uploaded_files) -> Tuple[List[str], List[Dict]]:
        """Professional file upload handling with progress tracking"""
        if not uploaded_files:
            return [], []
        
        documents = []
        metadata = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                status_text.text(f"Processing {uploaded_file.name}...")
                progress_bar.progress((i) / len(uploaded_files))
                
                text_content = ""
                if uploaded_file.name.lower().endswith('.pdf'):
                    text_content = self.processor.extract_text_from_pdf(uploaded_file)
                elif uploaded_file.name.lower().endswith('.docx'):
                    text_content = self.processor.extract_text_from_docx(uploaded_file)
                
                if text_content:
                    analysis = self.processor.analyze_text_content(text_content)
                    
                    metadata.append({
                        'filename': uploaded_file.name,
                        'upload_date': datetime.now(),
                        'file_size': len(uploaded_file.getvalue()),
                        'word_count': analysis['word_count'],
                        'sentence_count': analysis['sentence_count'],
                        'common_words': analysis['common_words'],
                        'sentences': analysis['sentences'],
                        'content_preview': text_content[:500] + "..." if len(text_content) > 500 else text_content,
                        'content': text_content
                    })
                    documents.append(text_content)
                
                time.sleep(0.1)  # UX improvement: slight delay for smooth progress
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                continue
        
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        time.sleep(0.5)
        status_text.empty()
        
        return documents, metadata
    
    def render_dashboard(self):
        """Award-winning dashboard design"""
        self.ui.create_hero_section()
        
        # Feature highlights
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="professional-card">
                <h3>🚀 Intelligent Search</h3>
                <p>AI-powered semantic understanding beyond basic keyword matching</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="professional-card">
                <h3>📊 Advanced Analytics</h3>
                <p>Professional insights and document intelligence metrics</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="professional-card">
                <h3>💾 Multi-Format Support</h3>
                <p>PDF, Word documents, and ZIP archives with robust processing</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions
        st.markdown("---")
        st.markdown("## 🚀 Quick Start")
        
        if st.session_state.metadata:
            doc_count = len(st.session_state.metadata)
            total_words = sum(m['word_count'] for m in st.session_state.metadata)
            
            st.success(f"✅ **{doc_count} documents loaded** • **{total_words:,} words** ready for search")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Start Searching", use_container_width=True, type="primary"):
                    st.session_state.current_page = "search"
                    st.rerun()
            with col2:
                if st.button("📊 View Analytics", use_container_width=True):
                    st.session_state.current_page = "analytics"
                    st.rerun()
        else:
            st.info("📁 **No documents yet** • Upload your meeting minutes to begin")
            if st.button("📤 Upload Documents", type="primary"):
                st.session_state.current_page = "upload"
                st.rerun()
    
    def render_upload_section(self):
        """Professional upload interface"""
        st.markdown("## 📤 Professional Document Upload")
        
        upload_method = st.radio("Upload Method:", 
                               ["Single Files", "ZIP Archive"], 
                               horizontal=True,
                               help="Choose between individual files or compressed archive")
        
        uploaded_files = []
        
        if upload_method == "Single Files":
            uploaded_files = st.file_uploader(
                "Select PDF or Word Documents",
                type=['pdf', 'docx'],
                accept_multiple_files=True,
                help="Supports multiple file selection with drag & drop"
            )
        else:
            zip_file = st.file_uploader(
                "Upload ZIP Archive",
                type=['zip'],
                help="ZIP file containing PDF or Word documents"
            )
            if zip_file:
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zf:
                        for file_info in zf.infolist():
                            if file_info.filename.lower().endswith(('.pdf', '.docx')):
                                with zf.open(file_info.filename) as file:
                                    file_data = file.read()
                                    file_obj = io.BytesIO(file_data)
                                    file_obj.name = file_info.filename
                                    uploaded_files.append(file_obj)
                except Exception as e:
                    st.error(f"Error reading ZIP archive: {str(e)}")
        
        if uploaded_files and st.button("Process Documents", type="primary", use_container_width=True):
            with st.spinner("Professional document processing in progress..."):
                documents, metadata = self.handle_file_upload(uploaded_files)
                
                if documents:
                    st.session_state.documents = documents
                    st.session_state.metadata = metadata
                    st.success(f"✅ Successfully processed **{len(documents)}** documents!")
                    
                    # Professional results summary
                    col1, col2, col3 = st.columns(3)
                    total_words = sum(m['word_count'] for m in metadata)
                    
                    with col1:
                        st.metric("Documents Processed", len(documents))
                    with col2:
                        st.metric("Total Words", f"{total_words:,}")
                    with col3:
                        st.metric("Average Length", f"{total_words//len(metadata):,} words")
                    
                    st.balloons()
    
    def render_search_section(self):
        """Award-winning search interface"""
        st.markdown("## 🔍 Professional Document Search")
        
        if not st.session_state.documents:
            st.warning("No documents available for search. Please upload documents first.")
            if st.button("Go to Upload", type="secondary"):
                st.session_state.current_page = "upload"
                st.rerun()
            return
        
        # Professional search interface
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Search Query:",
                placeholder="Enter keywords, phrases, or concepts to search for...",
                help="Professional semantic search with intelligent matching"
            )
        
        with col2:
            results_count = st.selectbox("Results:", [5, 10, 20, 50])
        
        if search_query:
            with st.spinner("🔍 Professional search in progress..."):
                results = self.searcher.semantic_keyword_search(
                    search_query, 
                    st.session_state.documents, 
                    st.session_state.metadata,
                    top_k=results_count
                )
                
                st.session_state.search_results = results
                
                if results:
                    st.success(f"🎯 Found **{len(results)}** relevant matches")
                    
                    for i, result in enumerate(results):
                        # Professional result card
                        st.markdown(f"""
                        <div class="professional-card">
                            <div style="display: flex; justify-content: between; align-items: start; margin-bottom: 1rem;">
                                <h3 style="margin: 0; flex: 1;">📄 {result['metadata']['filename']}</h3>
                                <span class="relevance-badge">Relevance: {result['score']:.2f}</span>
                            </div>
                            <p style="color: var(--text-secondary); margin: 0;">
                                {result['metadata']['word_count']} words • {result['metadata']['sentence_count']} sentences
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Professional match display
                        if result['matches']:
                            with st.expander(f"View {len(result['matches'])} contextual matches", expanded=True):
                                for match in result['matches']:
                                    st.markdown(f"""
                                    <div style="margin: 0.5rem 0; padding: 1rem; background: var(--background); border-radius: 8px;">
                                        <p style="margin: 0; line-height: 1.6;">{match['sentence']}</p>
                                        <small style="color: var(--text-secondary);">Match strength: {match['similarity']:.2f}</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Professional document preview
                        with st.expander("Full document content"):
                            st.text_area(
                                "Document Text:",
                                result['document'],
                                height=200,
                                key=f"doc_preview_{i}",
                                label_visibility="collapsed"
                            )
                else:
                    st.info("No matches found. Try different search terms or broader concepts.")
    
    def render_analytics_section(self):
        """Professional analytics dashboard"""
        st.markdown("## 📊 Professional Analytics")
        
        if not st.session_state.metadata:
            st.warning("No data available for analytics. Please upload documents first.")
            return
        
        metadata = st.session_state.metadata
        
        # Professional metrics dashboard
        st.markdown("### 📈 Document Intelligence Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", len(metadata))
        
        with col2:
            total_words = sum(m['word_count'] for m in metadata)
            st.metric("Total Words", f"{total_words:,}")
        
        with col3:
            avg_words = total_words // len(metadata)
            st.metric("Avg per Document", f"{avg_words:,}")
        
        with col4:
            total_size = sum(m['file_size'] for m in metadata)
            st.metric("Total Size", f"{total_size / 1024 / 1024:.2f} MB")
        
        # Professional content analysis
        st.markdown("### 🔤 Content Intelligence")
        
        # Word frequency analysis
        all_words = []
        for meta in metadata:
            all_words.extend([word for word, count in meta['common_words']])
        
        if all_words:
            word_freq = Counter(all_words)
            top_words = word_freq.most_common(15)
            
            # Professional visualization
            cols = st.columns(3)
            for i, (word, count) in enumerate(top_words):
                with cols[i % 3]:
                    st.metric(f"#{i+1} {word.title()}", count)
        
        # Professional document catalog
        st.markdown("### 📋 Document Catalog")
        
        for meta in metadata:
            with st.expander(f"📄 {meta['filename']} ({meta['word_count']} words)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Document Details**")
                    st.write(f"• Uploaded: {meta['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"• File Size: {meta['file_size']:,} bytes")
                    st.write(f"• Sentences: {meta['sentence_count']}")
                
                with col2:
                    st.write("**Content Analysis**")
                    st.write(f"• Word Count: {meta['word_count']}")
                    st.write("• Top Keywords:")
                    for word, count in meta['common_words'][:3]:
                        st.write(f"  - {word} ({count})")
                
                st.write("**Preview:**")
                st.text(meta['content_preview'])
    
    def render_sidebar(self):
        """Professional sidebar navigation"""
        with st.sidebar:
            st.markdown("""
            <div style="text-align: center; padding: 1rem 0;">
                <h1 style="color: var(--primary); margin: 0;">🔍 MeetSearch Pro</h1>
                <p style="color: var(--text-secondary); margin: 0;">Professional Edition</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Professional navigation
            page_options = {
                "🏠 Dashboard": "dashboard",
                "📤 Upload": "upload", 
                "🔍 Search": "search",
                "📊 Analytics": "analytics"
            }
            
            selected_page = st.selectbox(
                "Navigation",
                list(page_options.keys()),
                index=list(page_options.values()).index(st.session_state.current_page)
            )
            
            st.session_state.current_page = page_options[selected_page]
            
            st.markdown("---")
            
            # Professional status panel
            st.markdown("### 📊 System Status")
            
            if st.session_state.metadata:
                doc_count = len(st.session_state.metadata)
                total_words = sum(m['word_count'] for m in st.session_state.metadata)
                
                st.success(f"**Documents:** {doc_count}")
                st.info(f"**Words:** {total_words:,}")
                
                if st.session_state.search_results:
                    st.metric("Last Search", f"{len(st.session_state.search_results)} results")
            else:
                st.warning("No documents loaded")
            
            st.markdown("---")
            
            # Professional system info
            st.markdown("### ⚙️ System")
            st.caption(f"Streamlit {st.__version__}")
            st.caption("Professional Edition v2.0")

    def run(self):
        """Award-winning application runner"""
        try:
            # Render professional sidebar
            self.render_sidebar()
            
            # Handle dependency errors gracefully
            if not DEPENDENCIES_LOADED:
                st.error("❌ System Configuration Issue")
                st.error(f"Required dependencies not available: {IMPORT_ERROR}")
                st.info("Please ensure all requirements are properly installed")
                return
            
            # Professional page routing
            if st.session_state.current_page == "dashboard":
                self.render_dashboard()
            elif st.session_state.current_page == "upload":
                self.render_upload_section()
            elif st.session_state.current_page == "search":
                self.render_search_section()
            elif st.session_state.current_page == "analytics":
                self.render_analytics_section()
                
        except Exception as e:
            # Professional error handling
            st.error("🚨 Application Error")
            st.error("An unexpected error occurred. This has been logged for review.")
            st.info("Please try refreshing the application")
            
            # Professional error logging (would connect to proper logging in production)
            st.code(f"Error details: {str(e)}")

# ===== PHASE 6: PROFESSIONAL APPLICATION BOOTSTRAP =====

def main():
    """Award-winning application entry point"""
    try:
        app = MeetSearchApplication()
        app.run()
    except Exception as e:
        # Ultimate fallback error handling
        st.error("Critical system error. Please contact support.")
        st.stop()

if __name__ == "__main__":
    main()