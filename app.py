import streamlit as st

# ONLY this at top level - no other Streamlit calls, no session state
st.set_page_config(
    page_title="MeetSearch Pro",
    page_icon="🔍",
    layout="wide"
)

def main():
    """All app code lives here"""
    # Initialize session state safely
    if 'docs' not in st.session_state:
        st.session_state.docs = []
        st.session_state.meta = []
    
    # App UI
    st.title("🔍 MeetSearch Pro")
    st.write("Upload and search meeting minutes")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose PDF or DOCX files",
        type=['pdf', 'docx'],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("Process Files"):
        process_files(uploaded_files)
    
    # Search functionality
    if st.session_state.docs:
        search_interface()
    else:
        st.info("Upload documents to enable search")
    
    # Analytics
    if st.session_state.meta:
        show_analytics()

def process_files(uploaded_files):
    """Process uploaded files"""
    from docx import Document
    import PyPDF2
    import re
    
    new_docs = []
    new_meta = []
    
    for file in uploaded_files:
        text = ""
        try:
            if file.name.lower().endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
            elif file.name.lower().endswith('.docx'):
                doc = Document(file)
                text = " ".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            st.error(f"Error with {file.name}: {str(e)}")
            continue
        
        if text and len(text.strip()) > 10:
            words = len(text.split())
            new_docs.append(text)
            new_meta.append({
                'name': file.name,
                'words': words,
                'text': text
            })
    
    if new_docs:
        st.session_state.docs = new_docs
        st.session_state.meta = new_meta
        st.success(f"Processed {len(new_docs)} documents!")

def search_interface():
    """Search functionality"""
    query = st.text_input("Search for:")
    
    if query:
        results = []
        for doc, meta in zip(st.session_state.docs, st.session_state.meta):
            if query.lower() in doc.lower():
                results.append((meta['name'], doc, meta))
        
        if results:
            st.write(f"Found {len(results)} matches:")
            for name, doc, meta in results:
                with st.expander(f"{name} - {meta['words']} words"):
                    st.write(doc[:1000] + "..." if len(doc) > 1000 else doc)
        else:
            st.info("No matches found")

def show_analytics():
    """Show analytics"""
    meta = st.session_state.meta
    st.write(f"**Documents:** {len(meta)}")
    total_words = sum(m['words'] for m in meta)
    st.write(f"**Total words:** {total_words}")
    st.write(f"**Average per document:** {total_words // len(meta)}")

# REQUIRED: This conditional ensures proper initialization
if __name__ == "__main__":
    main()