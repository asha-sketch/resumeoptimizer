import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Signal Optimizer", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"Setup Error: {str(e)}")
else:
    st.error("Missing Secret: Please add GOOGLE_API_KEY to your Streamlit Secrets.")

# --- 2. THE IMPROVED AI BRAIN ---
def get_ai_rewrite(resume_text, jd_text):
    # These are the exact official names. We try 'models/' prefix first.
    models_to_try = [
        'models/gemini-1.5-flash', 
        'models/gemini-1.5-pro', 
        'models/gemini-pro',
        'gemini-1.5-flash',
        'gemini-pro'
    ]
    
    prompt = f"Rewrite this resume for this JD. Tone: Humble/Confident. Resume: {resume_text} JD: {jd_text} ... [IMPORTANT: Start with KEYWORDS: then DRAFT:]"

    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # If we get here, it worked!
            return response.text
        except Exception as e:
            last_error = str(e)
            continue 
            
    # If all fail, show the specific reason why the last one failed
    st.error(f"All models failed. Last Error: {last_error}")
    st.info("Note: If you are in the UK/EU, you may need to use a VPN or an OpenAI key.")
    return None

# --- 3. UI & HELPERS (Keep these the same) ---
def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

def create_docx(text):
    doc = Document()
    clean_text = re.sub(r'\[(?:ACTION|QUERY): .*?\]', '', text) 
    for para in clean_text.split('\n'):
        if para.strip(): doc.add_paragraph(para)
    bio = BytesIO()
    doc.save(bio); bio.seek(0)
    return bio

st.title("🚀 Beta: Resume Signal Optimizer")

with st.sidebar:
    st.header("Upload Inputs")
    uploaded_file = st.file_uploader("Upload Resume", type="pdf")
    jd_input = st.text_area("Paste JD", height=300)
    
    if st.button("Generate Beta Draft"):
        if uploaded_file and jd_input:
            resume_text = extract_pdf_text(uploaded_file)
            output = get_ai_rewrite(resume_text, jd_input)
            if output and "DRAFT:" in output:
                parts = output.split("DRAFT:")
                st.session_state['keywords'] = parts[0].replace("KEYWORDS:", "").strip().split(", ")
                st.session_state['draft'] = parts[1].strip()
                st.session_state['actions'] = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
        else:
            st.warning("Input required.")

    st.divider()
    if st.checkbox("Check Available AI Models"):
        try:
            m_list = [m.name for m in genai.list_models()]
            st.write(m_list)
        except Exception as e:
            st.write(f"Diagnostic failed: {str(e)}")

# Main Display
if 'draft' in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        for kw in st.session_state['keywords']:
            st.write(f"{'✅' if kw.lower() in st.session_state['draft'].lower() else '⬜'} {kw}")
    with c2:
        st.session_state['draft'] = st.text_area("Editor", value=st.session_state['draft'], height=600)
    with c3:
        tags = re.findall(r'\[(?:ACTION|QUERY): (.*?)\]', st.session_state['draft'])
        for item in st.session_state['actions']:
            st.write(f"{'✅ ~~' + item + '~~' if item not in tags else '👉 ' + item}")
        if not tags:
            st.download_button("📥 Download", data=create_docx(st.session_state['draft']), file_name="Resume.docx")
