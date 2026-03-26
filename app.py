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
    .reportview-container { background: #f0f2f6; }
    .stTextArea textarea { font-family: 'Courier New', Courier, monospace; }
    .action-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_content_type=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key. Check your Streamlit Secrets.")

# --- 2. AI AUDIT LOGIC ---
def run_ai_audit(resume_text, jd_text):
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    You are a Hiring Manager at a top-tier company. Perform a 3-part audit of this resume based on the Job Description (JD).

    PART 1: KEYWORD GAP ANALYSIS
    - Identify 8 essential keywords from the JD. 
    - For each, state if it is [FOUND] or [MISSING] in the resume. 
    - For [MISSING] keywords, provide a specific 'Suggestion' on how to incorporate it.

    PART 2: METRIC HUNTER
    - Identify bullet points in the resume that lack quantifiable impact (numbers, %, $). 
    - Flag these in the draft using [METRIC_NEEDED: 'Why this needs a number'].

    PART 3: LINGUISTIC MIRRORING (THE DRAFT)
    - Rewrite the resume using the exact 'language' and 'tone' of the JD.
    - If the JD values 'Autonomy', ensure the resume reflects that. 
    - If the JD uses specific terminology (e.g., 'Stakeholders' vs 'Clients'), use the JD's version.

    RESUME: {resume_text}
    JD: {jd_text}

    OUTPUT FORMAT:
    KEYWORDS_ANALYSIS: [List each keyword with FOUND/MISSING and a Suggestion]
    DRAFT: [The mirrored rewrite with [METRIC_NEEDED] and [KEYWORD_MISSING: 'Suggested Phrase'] tags inserted]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Audit Error: {str(e)}")
        return None

def create_docx(text):
    doc = Document()
    # Strip all AI tags before final export
    clean_text = re.sub(r'\[(?:METRIC_NEEDED|KEYWORD_MISSING): .*?\]', '', text) 
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. THE UI ---
st.title("🎯 Resume Signal Auditor")
st.warning("⚠️ **AI Disclaimer:** This output is AI-generated and can make mistakes. It is a tool to bolster your narrative, but human judgment and factual verification are required before applying.")

with st.sidebar:
    st.header("1. Data Ingestion")
    uploaded_file = st.file_uploader("Upload Current Resume (PDF)", type="pdf")
    jd_input = st.text_area("Target Job Description", height=300)
    
    if st.button("Run Strategic Audit", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Auditing signals and mirroring language..."):
                with pdfplumber.open(uploaded_file) as pdf:
                    resume_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                output = run_ai_audit(resume_text, jd_input)
                
                if output and "DRAFT:" in output:
                    st.session_state['analysis'] = output.split("DRAFT:")[0].replace("KEYWORDS_ANALYSIS:", "").strip()
                    st.session_state['draft'] = output.split("DRAFT:")[1].strip()
                    # Extract the items the user MUST address
                    st.session_state['todo_items'] = re.findall(r'\[(?:METRIC_NEEDED|KEYWORD_MISSING): (.*?)\]', st.session_state['draft'])
        else:
            st.warning("Please upload a PDF and paste a JD.")

# --- 4. THE AUDIT DASHBOARD ---
if 'draft' in st.session_state:
    
    col_left, col_right = st.columns([1.5, 1], gap="large")

    with col_left:
        st.subheader("✍️ Rewritten Draft (Linguistic Mirroring)")
        st.caption("The text below has been mirrored to match the JD's language. Please resolve the bracketed items.")
        st.session_state['draft'] = st.text_area("Live Editor", value=st.session_state['draft'], height=700, label_visibility="collapsed")

    with col_right:
        st.subheader("📋 Action Items Box")
        
        # Keyword Analysis Expander
        with st.expander("🔍 Keyword Gap Analysis", expanded=False):
            st.write(st.session_state['analysis'])

        st.write("### Required Fixes")
        current_tags = re.findall(r'\[(?:METRIC_NEEDED|KEYWORD_MISSING): (.*?)\]', st.session_state['draft'])
        
        # Check if items are resolved
        resolved_all = True
        for item in st.session_state['todo_items']:
            if item in current_tags:
                st.error(f"👉 {item}")
                resolved_all = False
            else:
                st.success(f"✅ ~~{item}~~")
        
        st.divider()
        
        if resolved_all:
            st.balloons()
            st.success("Audit Complete! Your resume is now high-signal and data-dense.")
            st.download_button("📥 Download Verified .docx", data=create_docx(st.session_state['draft']), file_name="Audited_Resume.docx", use_container_width=True)
        else:
            st.button("Download Locked", disabled=True, use_container_width=True)
            st.info("The download button will unlock once you address all [METRIC_NEEDED] and [KEYWORD_MISSING] items in the editor.")

else:
    st.info("Upload your resume and the job description to start the audit.")
