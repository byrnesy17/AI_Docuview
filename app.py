import streamlit as st

# CRITICAL: This MUST be the absolute first Streamlit command
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide"
)

# Now import other stuff
import zipfile
import io
from datetime import datetime
import re
from collections import Counter

try:
    from docx import Document
    import PyPDF2
except ImportError as e:
    st.error(f"Missing dependencies: {e}")

# Initialize app state safely
if 'docs' not in st.session_state:
    st.session_state.docs = []
    st.session_state.meta = []

# Modern CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 10px;
        background: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #4ECDC4;
    }
    .highlight {
        background: #FFEB3B;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# App functions
def extract_text(file):
    if file.name.lower().endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(file)
            return " ".join([page.extract_text() or "" for page in reader.pages])
        except:
            return ""
    elif file.name.lower().endswith('.docx'):
        try:
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs if p.text])
        except:
            return ""
    return ""

def search_docs(query, docs, meta):
    results = []
    query = query.lower()
    for i, (doc, m) in enumerate(zip(docs, meta)):
        if query in doc.lower():
            # Simple highlight
            highlighted = re.sub(f'({re.escape(query)})', 
                               r'<span class="highlight">\1</span>', 
                               doc, flags=re.IGNORECASE)
            results.append((m['name'], highlighted, m))
    return results

# Main app
st.markdown('<div class="main-header">🔍 MeetSearch Pro</div>', unsafe_allow_html=True)

# Tabs for navigation
tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔍 Search", "📊 Analytics"])

with tab1:
    st.header("Upload Meeting Minutes")
    
    upload_option = st.radio("Upload type:", ["Files", "ZIP"], horizontal=True)
    
    uploaded_files = []
    if upload_option == "Files":
        uploaded_files = st.file_uploader("Select PDF/DOCX files", 
                                        type=['pdf', 'docx'], 
                                        accept_multiple_files=True)
    else:
        zip_file = st.file_uploader("Upload ZIP", type=['zip'])
        if zip_file:
            with zipfile.ZipFile(zip_file) as z:
                for name in z.namelist():
                    if name.lower().endswith(('.pdf', '.docx')):
                        with z.open(name) as f:
                            file_data = f.read()
                            file_obj = io.BytesIO(file_data)
                            file_obj.name = name
                            uploaded_files.append(file_obj)
    
    if uploaded_files and st.button("Process", type="primary"):
        with st.spinner("Processing..."):
            new_docs = []
            new_meta = []
            for file in uploaded_files:
                text = extract_text(file)
                if text and len(text) > 10:
                    words = len(re.findall(r'\w+', text))
                    new_docs.append(text)
                    new_meta.append({
                        'name': file.name,
                        'words': words,
                        'date': datetime.now(),
                        'size': len(file.getvalue())
                    })
            
            if new_docs:
                st.session_state.docs = new_docs
                st.session_state.meta = new_meta
                st.success(f"✅ Processed {len(new_docs)} documents!")
                st.balloons()

with tab2:
    st.header("Search Documents")
    
    if not st.session_state.docs:
        st.warning("Upload documents first")
    else:
        query = st.text_input("Search query:")
        if query:
            results = search_docs(query, st.session_state.docs, st.session_state.meta)
            if results:
                st.success(f"Found {len(results)} matches:")
                for name, highlighted, meta in results:
                    with st.expander(f"📄 {name} ({meta['words']} words)"):
                        st.markdown(f"**Matching content:**")
                        st.markdown(highlighted[:500] + "..." if len(highlighted) > 500 else highlighted, 
                                  unsafe_allow_html=True)
            else:
                st.info("No matches found")

with tab3:
    st.header("Analytics")
    
    if not st.session_state.meta:
        st.info("Upload documents to see analytics")
    else:
        col1, col2, col3 = st.columns(3)
        total_words = sum(m['words'] for m in st.session_state.meta)
        
        with col1:
            st.metric("Documents", len(st.session_state.meta))
        with col2:
            st.metric("Total Words", f"{total_words:,}")
        with col3:
            st.metric("Avg per Doc", f"{total_words//len(st.session_state.meta):,}")
        
        st.subheader("Document List")
        for meta in st.session_state.meta:
            st.write(f"**{meta['name']}** - {meta['words']} words")

# Make sure the app actually runs
if __name__ == "__main__":
    pass