import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & STYLE ---
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

# API Key Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key. Please add 'GOOGLE_API_KEY' to Streamlit Secrets.")

# --- 2. AI LOGIC ---
def run_ai_audit(resume_text, jd_text):
    models_to_try = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    prompt = f"""
    You are an elite Career Coach.
    
    TASK:
    1. Summarize 3-4 specific tone/vocabulary pivots in the CHANGELOG section.
    2. Rewrite the resume DRAFT to mirror the JD's language. 
    3. Maintain a 'Humble but Confident' tone.
    4. Use ONLY [INSERT: specific data] where a metric or fact is missing.
    5. RETAIN the original resume's structure exactly. No extra bolding (**).

    FORMAT:
    CHANGELOG:
    (Brief summary)
    
    DRAFT:
    (Full rewritten resume)

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

# --- 3. HELPERS ---
def create_docx(text):
    doc = Document()
    # Remove [INSERT: ...] tags for final version
    clean = re.sub(r'\[INSERT:? .*?\]', '', text, flags=re.IGNORECASE) 
    for line in clean.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            # Basic bolding for headers
            if "|" in line or line.isupper():
                p.add_run(line).bold = True
            else:
                p.add_run(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. SIDEBAR INPUTS ---
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
                    # Identify items for the checklist
                    st.session_state['todo_items'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['draft'])
                else:
                    st.error("AI Error. Please try again.")

# --- 5. MAIN DASHBOARD ---
if 'draft' in st.session_state:
    
    # Changelog / Strategy
    with st.expander("🛠️ AI Strategy: What was rewritten", expanded=True):
        st.write(st.session_state['changelog'])

    # Two Column Layout
    col_ed, col_check = st.columns([2, 1], gap="large")

    with col_ed:
        st.subheader("✍️ Draft & Ed
