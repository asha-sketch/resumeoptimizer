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
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"Setup Error: {str(e)}")
else:
    st.error("Missing Secret: Please add GOOGLE_API_KEY to your Streamlit Secrets.")

# --- 2. THE AI BRAIN (Updated for 2024 Models) ---
def get_ai_rewrite(resume_text, jd_text):
    # We will try the two most common stable model names
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro']
    
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

    success = False
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
            success = True
            break
        except Exception:
            continue # Try the next model if this one fails
            
    if not success:
        st.error("Google AI Error: Could not find a working model. Please check the sidebar for 'Available Models'.")
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

with st.sidebar:
    st.header("Upload Inputs")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Paste Job Description", height=300)
    
    if st.button("Generate Beta Draft", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Analyzing signals with Gemini 1.5..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = get_ai_rewrite(resume_text, jd_input)
                
                if output:
                    if "DRAFT:" in output:
                        parts = output.split("DRAFT:")
                        st.session_state['keywords'] = parts[0].replace("KEYWORDS:", "").strip().split(", ")
                        st.session_state['draft'] = parts[1].strip()
                        st.session_state['actions'] = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
                    else:
                        st.warning("The AI output format was unexpected. Try clicking the button again.")
        else:
            st.warning("Please upload a PDF and paste a JD first.")

    st.divider()
    # Diagnostic Tool: Helps us find the right model name if it fails again
    if st.checkbox("Check Available AI Models"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(models)
        except Exception as e:
            st.write("Could not list models.")

# Main Interface
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
        st.session_state['draft'] = st.text_area("Live Editor", value=st.session_state['draft'], height=600, label_visibility="collapsed")

    with col_aud:
        st.header("📋 To-Do")
        current_tags = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
        for item in st.session_state['actions']:
            if item in current_tags:
                st.warning(f"👉 {item}")
            else:
                st.write(f"✅ ~~{item}~~")
        
        st.divider()
        if not current_tags:
            st.success("Ready!")
            docx_file = create_docx(st.session_state['draft'])
            st.download_button("📥 Download Word Doc", data=docx_file, file_name="Optimized_Resume.docx")
        else:
            st.button("Download Locked", disabled=True)
else:
    st.info("👋 Upload your Resume and the Job Description to start.")
