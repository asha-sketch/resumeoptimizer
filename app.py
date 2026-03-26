import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP & BRANDING ---
st.set_page_config(page_title="Resume Signal Auditor", layout="wide")

# Custom CSS for the Professional Audit Dashboard
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTextArea textarea { font-family: 'Courier New', Courier, monospace; font-size: 14px; line-height: 1.6; }
    .action-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# API Key Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key. Please add 'GOOGLE_API_KEY' to your Streamlit Secrets.")

# --- 2. AI AUDIT LOGIC (Robust Formatting) ---
def run_ai_audit(resume_text, jd_text):
    # Trying the most stable models from your diagnostic list
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-flash-latest']
    
    prompt = f"""
    You are a Hiring Manager. Perform a strategic audit of this resume based on the JD.

    PART 1: KEYWORD GAP ANALYSIS
    - Identify 8 essential keywords from the JD. State if [FOUND] or [MISSING].

    PART 2: METRIC HUNTER & LINGUISTIC MIRRORING
    - Rewrite the resume to mirror the JD's language and 'Humble but Confident' tone.
    - CRITICAL: For ANY bullet point that lacks a number, %, or $ amount, you MUST insert the tag [METRIC_NEEDED: 'reason'].
    - CRITICAL: If a major keyword is missing from a section, insert [KEYWORD_MISSING: 'keyword'].
    
    RESUME: {resume_text}
    JD: {jd_text}

    OUTPUT FORMAT:
    KEYWORDS_ANALYSIS: [List here]
    DRAFT: [The full rewrite with the [METRIC_NEEDED: ...] and [KEYWORD_MISSING: ...] tags included]
    """
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue
    return None

# --- 3. HELPER FUNCTIONS ---
def extract_pdf_text(file):
    try:
        with pdfplumber.open(file) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    except Exception as e:
        return ""

def create_docx(text):
    doc = Document()
    # Flexible regex to remove all bracketed AI tags for the final doc
    clean_text = re.sub(r'\[(METRIC_NEEDED|KEYWORD_MISSING|ACTION|QUERY):?.*?\]', '', text, flags=re.IGNORECASE) 
    for line in clean_text.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            # Bolding headers
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
st.warning("⚠️ **AI Disclaimer:** This tool assists your narrative. Please verify all metrics and facts before applying.")

with st.sidebar:
    st.header("1. Input Data")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_input = st.text_area("Target Job Description", height=300)
    
    if st.button("Run Strategic Audit", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Analyzing signals..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = run_ai_audit(resume_text, jd_input)
                
                if output and "DRAFT:" in output:
                    st.session_state['analysis'] = output.split("DRAFT:")[0].replace("KEYWORDS_ANALYSIS:", "").strip()
                    st.session_state['draft'] = output.split("DRAFT:")[1].strip()
                    
                    # Identifies tags in the generated text
                    raw_tags = re.findall(r'\[(.*?):?\s*(.*?)\]', st.session_state['draft'])
                    st.session_state['todo_items'] = [f"[{t[0]}: {t[1]}]" for t in raw_tags if any(word in t[0].upper() for word in ["METRIC", "KEYWORD", "ACTION"])]
                else:
                    st.error("AI Error: Formatting mismatch. Please try again.")

# --- 5. THE AUDIT DASHBOARD ---
if 'draft' in st.session_state:
    col_editor, col_checklist = st.columns([1.5, 1], gap="large")

    with col_editor:
        st.subheader("✍️ Rewritten Draft")
        st.caption("Instructions: Replace the [BRACKETED ITEMS] with your real-world data.")
        user_edits = st.text_area("Live Editor", value=st.session_state['draft'], height=700, label_visibility="collapsed")
        st.session_state['draft'] = user_edits

    with col_checklist:
        st.subheader("📋 Action Items")  # CHANGED: Renamed from 'Action Items Box'
        
        with st.expander("🔍 Keyword Gap Analysis"):
            st.write(st.session_state['analysis'])

        st.write("### Required Fixes")
        
        # Real-time resolution check
        resolved_all = True
        if st.session_state.get('todo_items'):
            for item_str in st.session_state['todo_items']:
                if item_str in st.session_state['draft']:
                    st.error(f"👉 {item_str.replace('[', '').replace(']', '')}")
                    resolved_all = False
                else:
                    st.success(f"✅ Resolved")
        else:
            st.info("No specific action items flagged. Review the draft for general improvements.")

        st.divider()
        
        # Download Logic
        if resolved_all and st.session_state.get('todo_items'):
            st.balloons()
            st.success("Audit Complete!")
            st.download_button("📥 Download .docx", data=create_docx(st.session_state['draft']), file_name="Optimized_Resume.docx", use_container_width=True)
        elif not st.session_state.get('todo_items'):
             st.download_button("📥 Download .docx (No items flagged)", data=create_docx(st.session_state['draft']), file_name="Optimized_Resume.docx", use_container_width=True)
        else:
            st.button("Download Locked", disabled=True, use_container_width=True)
else:
    st.info("👋 Upload your Resume and the Job Description in the sidebar to start the strategic audit.")
