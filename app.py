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

# --- 2. THE AI BRAIN ---
def run_ai_audit(resume_text, jd_text):
    # Using the models confirmed in your diagnostic list
    models_to_try = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    prompt = f"""
    You are an elite Career Coach.
    
    TASK:
    1. Summarize 3-4 specific vocabulary/tone changes you made in the CHANGELOG section.
    2. Rewrite the resume DRAFT to mirror the JD's language while maintaining a 'Humble but Confident' tone.
    3. Use ONLY [INSERT: specific data needed] where a metric or fact is missing. Do not use any other brackets or symbols.
    4. RETAIN the original resume's structure and formatting exactly. Do not add bolding (**) unless it was in the original text.

    FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
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
            # Bolding headers (standard detection for names/titles)
            if "|" in line or line.isupper():
                p.add_run(line).bold = True
            else:
                p.add_run(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
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
    
    # Strategy Section
    with st.expander("🛠️ AI Strategy: What was rewritten", expanded=True):
        st.write(st.session_state['changelog'])

    col_ed, col
