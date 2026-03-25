import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="Resume Signal Optimizer", layout="wide")

# Connect to Google Gemini
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Please add your GOOGLE_API_KEY to Streamlit Secrets.")

# --- 2. HELPER FUNCTIONS ---

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

def get_ai_rewrite(resume_text, jd_text):
    prompt = f"""
    You are an elite Career Coach. Optimize this resume for the provided Job Description (JD).
    
    TONE: Humble but Confident. No 'visionary' or 'rockstar' talk. Use ownership verbs.
    STRATEGY: 
    1. Identify 8 high-signal keywords from the JD.
    2. Rewrite the resume to show 'Staff-level' impact (flywheels, strategy, cross-functional).
    3. Insert [ACTION: ...] for missing metrics and [QUERY: ...] for fact-checks.
    
    RESUME: {resume_text}
    JD: {jd_text}
    
    IMPORTANT: Start your response with 'KEYWORDS:' followed by the list. 
    Then write 'DRAFT:' followed by the full rewritten resume.
    """
    response = model.generate_content(prompt)
    return response.text

def create_docx(text):
    doc = Document()
    clean_text = re.sub(r'\[(?:ACTION|QUERY): .*?\]', '', text) # Remove tags for final doc
    for para in clean_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. THE UI LAYOUT ---

st.title("🚀 Beta: Resume Signal Optimizer (Powered by Gemini)")

# Sidebar for Inputs
with st.sidebar:
    st.header("Upload Inputs")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Paste Job Description", height=300)
    
    if st.button("Generate Beta Draft", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Gemini is analyzing signals..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = get_ai_rewrite(resume_text, jd_input)
                
                # Split AI response into Keywords and Resume
                parts = output.split("DRAFT:")
                st.session_state['keywords'] = parts[0].replace("KEYWORDS:", "").strip().split(", ")
                st.session_state['draft'] = parts[1].strip()
                # Find all the [ACTION] tags to track them
                st.session_state['actions'] = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])

# Main Screen Interaction
if 'draft' in st.session_state:
    col_signals, col_editor, col_audit = st.columns([1, 2, 1], gap="medium")

    # Column 1: Live Keyword Tracking
    with col_signals:
        st.header("🎯 Signals")
        for kw in st.session_state['keywords']:
            # Check if keyword is currently in the text area
            if kw.lower() in st.session_state['draft'].lower():
                st.success(f"✅ {kw}")
            else:
                st.info(f"⬜ {kw}")

    # Column 2: The Editor
    with col_editor:
        st.header("✍️ Editor")
        st.caption("Tone: Humble & Confident. Replace the [ACTION] items with your data.")
        st.session_state['draft'] = st.text_area("Editable Resume", value=st.session_state['draft'], height=600, label_visibility="collapsed")

    # Column 3: The Audit Checklist
    with col_audit:
        st.header("📋 To-Do")
        current_tags = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
        
        for item in st.session_state['actions']:
            if item in current_tags:
                st.warning(f"👉 {item}")
            else:
                st.write(f"✅ ~~{item}~~")
        
        st.divider()
        if not current_tags:
            st.success("Ready for Download!")
            docx_file = create_docx(st.session_state['draft'])
            st.download_button("📥 Download Final Word Doc", data=docx_file, file_name="Optimized_Resume.docx")
        else:
            st.button("Download Locked", disabled=True, help="Complete all To-Do items to unlock.")
else:
    st.info("Upload your Resume and JD in the sidebar to start.")
