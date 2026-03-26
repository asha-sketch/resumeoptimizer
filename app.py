import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Signal Auditor", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stTextArea textarea { 
        font-family: 'Arial', sans-serif; 
        font-size: 14px; 
        line-height: 1.5; 
        border: 1px solid #d1d1d1;
    }
    </style>
    """, unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key in Secrets.")

# --- 2. THE AI BRAIN (Focused on Clean Output) ---
def run_ai_audit(resume_text, jd_text):
    models_to_try = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    prompt = f"""
    You are an elite Career Coach.
    
    TASK:
    1. Summarize 3-4 specific vocabulary/tone changes you made in the CHANGELOG.
    2. Rewrite the resume DRAFT to mirror the JD's language while maintaining a 'Humble but Confident' tone.
    3. Use ONLY [INSERT: specific data needed] where a metric or fact is missing. Do not use any other brackets or symbols.
    4. RETAIN the original resume's structure and formatting exactly. Do not add bolding (**) unless it was in the original text.

    FORMAT YOUR RESPONSE:
    CHANGELOG:
    (Brief summary of tone/keyword pivots)
    
    DRAFT:
    (The full, clean resume rewrite)

    RESUME: {resume_text}
    JD: {jd_text}
    """
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response.text:
                return response.text
        except:
            continue
    return None

# --- 3. HELPER TOOLS ---
def create_docx(text):
    doc = Document()
    # Remove only the [INSERT: ] tags for the final version
    clean = re.sub(r'\[INSERT:? .*?\]', '', text, flags=re.IGNORECASE) 
    for line in clean.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            # Simple bolding for headers (all caps or contains |)
            if "|" in line or line.isupper(): p.add_run(line).bold = True
            else: p.add_run(line)
    bio = BytesIO(); doc.save(bio); bio.seek(0)
    return bio

# --- 4. THE UI ---
st.title("🎯 Resume Signal Auditor")

with st.sidebar:
    st.header("1. Input Data")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Target Job Description", height=250)
    
    if st.button("Run Strategic Audit", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Auditing..."):
                with pdfplumber.open(uploaded_file) as pdf:
                    resume_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                raw_output = run_ai_audit(resume_text, jd_input)
                
                if raw_output and "DRAFT:" in raw_output:
                    st.session_state['changelog'] = raw_output.split("DRAFT:")[0].replace("CHANGELOG:", "").strip()
                    st.session_state['draft'] = raw_output.split("DRAFT:")[1].strip()
                    # Store the specific strings the user needs to replace
                    st.session_state['todo_items'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['draft'])
                else:
                    st.error("Processing error. Please click 'Run Strategic Audit' again.")

# --- 5. THE DASHBOARD ---
if 'draft' in st.session_state:
    
    # Changelog tells them WHAT was rewritten
    with st.expander("🛠️ Strategy: What was rewritten", expanded=True):
        st.write(st.session_state['changelog'])

    col_ed, col_check = st.columns([2, 1], gap="large")

    with col_ed:
        st.subheader("✍️ Draft & Editor")
        st.caption("Instructions: Address the [INSERT] tags below with your specific metrics.")
        # Only the editor is shown here, no "Preview" pane
        st.session_state['draft'] = st.text_area("Resume Content", value=st.session_state['draft'], height=650, label_visibility="collapsed")

    with col_check:
        st.subheader("📋 Action Items")
        st.write("Fill in these missing metrics to unlock your download.")
        
        # Check current text area for remaining [INSERT] tags
        current_tags_in_text = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['draft'])
        
        resolved_count = 0
        if 'todo_items' in st.session_state and st.session_state['todo_items']:
            for item in st.session_state['todo_items']:
                if item in current_tags_in_text:
                    st.error(f"👉 {item}")
                else:
                    st.success(f"✅ Resolved")
                    resolved_count += 1
            
            # Show progress
            total = len(st.session_state['todo_items'])
            if r
