import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="Resume Signal Optimizer", layout="wide")

# Connect using your Google Key
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"Setup Error: {str(e)}")
else:
    st.error("Missing Secret: Please add GOOGLE_API_KEY to your Streamlit Secrets.")

# --- 2. THE AI BRAIN (Matched to your specific models) ---
def get_ai_rewrite(resume_text, jd_text):
    # Based on your diagnostic list, these are the best working models for you:
    models_to_try = [
        'models/gemini-2.0-flash', 
        'models/gemini-1.5-flash', 
        'models/gemini-flash-latest'
    ]
    
    prompt = f"""
    You are an elite Career Coach. Optimize this resume for the provided Job Description (JD).
    
    TONE: Humble but Confident. No 'visionary' or 'rockstar' talk. Use ownership verbs.
    STRATEGY: 
    1. Identify 8 high-signal keywords from the JD.
    2. Rewrite the resume to show 'Staff-level' impact (flywheels, strategy, cross-functional).
    3. Insert [ACTION: ...] for missing metrics and [QUERY: ...] for fact-checks.
    
    RESUME: {resume_text}
    JD: {jd_text}
    
    IMPORTANT: You MUST start your response with 'KEYWORDS:' followed by the list. 
    Then write 'DRAFT:' followed by the full rewritten resume content.
    """

    last_err = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_err = str(e)
            continue 
            
    st.error(f"Engine Error: {last_err}")
    return None

# --- 3. HELPER TOOLS ---
def extract_pdf_text(file):
    try:
        with pdfplumber.open(file) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    except Exception as e:
        st.error(f"PDF Error: {str(e)}")
        return ""

def create_docx(text):
    doc = Document()
    # Remove AI tags for final doc
    clean_text = re.sub(r'\[(?:ACTION|QUERY): .*?\]', '', text) 
    for para in clean_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. THE UI ---
st.title("🚀 Beta: Resume Signal Optimizer")
st.write("Optimizing for Staff-level Marketplace Roles")

with st.sidebar:
    st.header("Upload Inputs")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Paste Job Description", height=300)
    
    if st.button("Generate Beta Draft", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Analyzing signals with Gemini 2.0..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = get_ai_rewrite(resume_text, jd_input)
                
                if output:
                    if "DRAFT:" in output:
                        parts = output.split("DRAFT:")
                        st.session_state['keywords'] = parts[0].replace("KEYWORDS:", "").strip().split(", ")
                        st.session_state['draft'] = parts[1].strip()
                        st.session_state['actions'] = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
                    else:
                        st.warning("The AI output format was unexpected. Try clicking again.")
        else:
            st.warning("Please upload a PDF and paste a JD first.")

# Main Interface (Only shows after "Generate" is clicked)
if 'draft' in st.session_state:
    col_sig, col_ed, col_aud = st.columns([1, 2, 1], gap="medium")

    with col_sig:
        st.header("🎯 Signals")
        for kw in st.session_state['keywords']:
            if kw.lower() in st.session_state['draft'].lower():
                st.success(f"✅ {kw}")
            else:
                st.info(f"⬜ {kw}")

    with col_ed:
        st.header("✍️ Editor")
        st.caption("Instructions: Address the [ACTION] items by typing your data directly here.")
        st.session_state['draft'] = st.text_area("Live Editor", value=st.session_state['draft'], height=600, label_visibility="collapsed")

    with col_aud:
        st.header("📋 To-Do")
        # Find all tags currently in the text area
        current_tags = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
        
        for item in st.session_state['actions']:
            if item in current_tags:
                st.warning(f"👉 {item}")
            else:
                st.write(f"✅ ~~{item}~~")
        
        st.divider()
        if not current_tags:
            st.success("Ready for export!")
            docx_file = create_docx(st.session_state['draft'])
            st.download_button("📥 Download Word Doc", data=docx_file, file_name="Optimized_Resume.docx")
        else:
            st.button("Download Locked", disabled=True)
else:
    st.info("👋 Upload your data in the sidebar to begin.")
