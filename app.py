import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="Resume Signal Optimizer", layout="wide")

# This part connects to your Google Key
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"Setup Error: {str(e)}")
else:
    st.error("Missing Secret: Please add GOOGLE_API_KEY to your Streamlit Secrets.")

# --- 2. THE AI BRAIN ---
def get_ai_rewrite(resume_text, jd_text):
    try:
        # We try the newest model first
        model = genai.GenerativeModel('gemini-1.5-flash')
        
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

    except Exception as e:
        # If the first model fails, try the older 'gemini-pro' model
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            return response.text
        except Exception as e2:
            st.error(f"Google AI Error: {str(e2)}")
            return None

# --- 3. HELPER TOOLS ---
def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

def create_docx(text):
    doc = Document()
    # Remove the AI tags [ACTION] for the final document
    clean_text = re.sub(r'\[(?:ACTION|QUERY): .*?\]', '', text) 
    for para in clean_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. THE UI (Always renders) ---
st.title("🚀 Beta: Resume Signal Optimizer")
st.write("Target: Staff-level Marketplace Roles")

# Sidebar for Inputs
with st.sidebar:
    st.header("Upload Inputs")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Paste Job Description", height=300)
    
    if st.button("Generate Beta Draft", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Analyzing signals..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = get_ai_rewrite(resume_text, jd_input)
                
                if output:
                    # Split AI response into Keywords and Resume
                    if "DRAFT:" in output:
                        parts = output.split("DRAFT:")
                        st.session_state['keywords'] = parts[0].replace("KEYWORDS:", "").strip().split(", ")
                        st.session_state['draft'] = parts[1].strip()
                        st.session_state['actions'] = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
                    else:
                        st.error("AI returned a format I didn't expect. Please try clicking the button again.")
        else:
            st.warning("Please upload a PDF and paste a JD first.")

# Main Screen Interaction
if 'draft' in st.session_state:
    col_signals, col_editor, col_audit = st.columns([1, 2, 1], gap="medium")

    with col_signals:
        st.header("🎯 Signals")
        for kw in st.session_state['keywords']:
            if kw.lower() in st.session_state['draft'].lower():
                st.success(f"✅ {kw}")
            else:
                st.info(f"⬜ {kw}")

    with col_editor:
        st.header("✍️ Editor")
        st.caption("Instructions: Edit the text directly. Remove the [ACTION] items as you fill them in.")
        st.session_state['draft'] = st.text_area("Live Editor", value=st.session_state['draft'], height=600, label_visibility="collapsed")

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
            st.success("All items cleared!")
            docx_file = create_docx(st.session_state['draft'])
            st.download_button("📥 Download Word Doc", data=docx_file, file_name="Optimized_Resume.docx")
        else:
            st.button("Download Locked", disabled=True)
else:
    st.info("👋 Hello! Upload your Resume and the Job Description in the sidebar to get started.")
