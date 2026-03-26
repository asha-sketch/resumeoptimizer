import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & BRANDING ---
st.set_page_config(page_title="Resume Signal Auditor", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTextArea textarea { font-family: 'Courier New', Courier, monospace; font-size: 14px; line-height: 1.6; }
    .rewrite-highlight { color: #007bff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key in Secrets.")

# --- 2. THE AI BRAIN (More Robust Formatting) ---
def run_ai_audit(resume_text, jd_text):
    # Use the specific model names that worked for your key previously
    models_to_try = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash', 'models/gemini-flash-latest']
    
    prompt = f"""
    You are an elite Staff-level Career Coach.
    
    TASK:
    1. Identify 8 KEYWORDS from the JD.
    2. Write a 3-sentence CHANGELOG explaining your strategic pivots for this role.
    3. Rewrite the resume DRAFT.
       - Wrap your edits in {{REWRITE: phrase}}.
       - Insert [ACTION: instruction] for missing metrics.

    FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
    ---
    CHANGELOG:
    (Your 3 sentences)
    ---
    KEYWORDS:
    (Your 8 keywords)
    ---
    DRAFT:
    (The full resume)
    ---

    RESUME: {resume_text}
    JD: {jd_text}
    """
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue
    return f"ERROR: {last_error}"

# --- 3. HELPER TOOLS ---
def create_docx(text):
    doc = Document()
    # Clean tags: remove {REWRITE: } and [ACTION: ]
    clean = re.sub(r'\{(?:REWRITE): (.*?)\}', r'\1', text) 
    clean = re.sub(r'\[(?:ACTION|METRIC|QUERY):?.*?\]', '', clean, flags=re.IGNORECASE) 
    for line in clean.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
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
            with st.spinner("Analyzing..."):
                with pdfplumber.open(uploaded_file) as pdf:
                    resume_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                raw_output = run_ai_audit(resume_text, jd_input)
                
                # STICKY PARSING LOGIC
                if "DRAFT:" in raw_output:
                    try:
                        # Split by the '---' separators or the labels
                        st.session_state['changelog'] = raw_output.split("CHANGELOG:")[1].split("KEYWORDS:")[0].replace("---","").strip()
                        st.session_state['keywords'] = raw_output.split("KEYWORDS:")[1].split("DRAFT:")[0].replace("---","").strip()
                        st.session_state['draft'] = raw_output.split("DRAFT:")[1].split("---")[0].strip()
                        st.session_state['actions'] = re.findall(r'\[ACTION:? (.*?)\]', st.session_state['draft'])
                    except:
                        st.error("AI followed the wrong format. Please try again.")
                        st.session_state['raw_debug'] = raw_output # Save for debug
                else:
                    st.error("AI encountered an error or blocked the content.")
                    st.session_state['raw_debug'] = raw_output

# --- 5. THE DASHBOARD ---
if 'draft' in st.session_state:
    with st.expander("🛠️ AI Changelog (Strategy)", expanded=True):
        st.info(st.session_state['changelog'])
        st.write(f"**Keywords:** {st.session_state['keywords']}")

    col_ed, col_check = st.columns([1.8, 1], gap="large")

    with col_ed:
        st.subheader("✍️ Editor")
        # Visual Preview
        preview = st.session_state['draft'].replace("{REWRITE:", "📘 **").replace("}", "**").replace("[ACTION:", "🔴 **[ACTION:**").replace("]", "**]")
        st.markdown(preview)
        st.divider()
        st.session_state['draft'] = st.text_area("Edit Text Area", value=st.session_state['draft'], height=500)

    with col_check:
        st.subheader("📋 Actions")
        current_tags = re.findall(r'\[ACTION:? (.*?)\]', st.session_state['draft'])
        resolved = 0
        if st.session_state['actions']:
            for item in st.session_state['actions']:
                if item in current_tags: st.error(f"👉 {item}")
                else:
                    st.success("✅ Resolved")
                    resolved += 1
            if resolved == len(st.session_state['actions']):
                st.download_button("📥 Download .docx", data=create_docx(st.session_state['draft']), file_name="Optimized_Resume.docx", use_container_width=True)
        else:
            st.info("No specific actions. Review draft.")

# DEBUG SECTION
if 'raw_debug' in st.session_state:
    with st.expander("Show Debugging Info"):
        st.code(st.session_state['raw_debug'])
