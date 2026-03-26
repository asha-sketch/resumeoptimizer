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
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# API Key Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key. Please add 'GOOGLE_API_KEY' to your Streamlit Secrets.")

# --- 2. AI AUDIT LOGIC (With Model Fallbacks) ---
def run_ai_audit(resume_text, jd_text):
    # These are the models from your diagnostic list, prioritizing 2.5 series
    models_to_try = [
        'gemini-2.5-flash', 
        'gemini-2.5-pro', 
        'gemini-1.5-flash', 
        'gemini-flash-latest'
    ]
    
    prompt = f"""
    You are a Hiring Manager at a top-tier company. Perform a 3-part strategic audit of this resume based on the Job Description (JD).

    PART 1: KEYWORD GAP ANALYSIS
    - Identify 8 essential keywords/skills from the JD. 
    - For each, state if it is [FOUND] or [MISSING] in the resume. 
    - For [MISSING] keywords, provide a specific 'Suggestion' on how to incorporate it into a bullet point.

    PART 2: METRIC HUNTER
    - Scan the resume for bullet points that lack quantifiable impact (numbers, %, $, or scale). 
    - Flag these in the draft using [METRIC_NEEDED: 'Context of why a number is needed here'].

    PART 3: LINGUISTIC MIRRORING (THE DRAFT)
    - Rewrite the resume using the 'language' and 'vocabulary' of the JD to resonate with the hiring team.
    - Maintain a 'Humble but Confident' tone: Use ownership verbs but avoid arrogance.
    - If the JD uses specific terminology (e.g., 'Stakeholders' vs 'Clients'), use the JD's version.
    - HALLUCINATION GUARDRAIL: Do NOT invent or change company names, job titles, or dates.

    RESUME: {resume_text}
    JD: {jd_text}

    OUTPUT FORMAT:
    KEYWORDS_ANALYSIS: [List keywords with status and suggestions]
    DRAFT: [The mirrored rewrite with [METRIC_NEEDED] and [KEYWORD_MISSING: 'Phrase'] tags inserted]
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
        st.error(f"PDF Error: {str(e)}")
        return ""

def create_docx(text):
    doc = Document()
    # Strip all AI tags [ACTION/METRIC/KEYWORD] before final export
    clean_text = re.sub(r'\[(?:METRIC_NEEDED|KEYWORD_MISSING): .*?\]', '', text) 
    for line in clean_text.split('\n'):
        if line.strip():
            # Apply bold to headers (usually lines with pipes or all caps)
            if "|" in line or line.isupper():
                p = doc.add_paragraph()
                p.add_run(line).bold = True
            else:
                doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. THE UI INTERFACE ---
st.title("🎯 Resume Signal Auditor")
st.warning("⚠️ **Disclaimer:** This tool uses AI to bolster your narrative. Factual accuracy remains your responsibility. Falsifying data on a resume is never recommended.")

with st.sidebar:
    st.header("1. Input Data")
    uploaded_file = st.file_uploader("Upload Current Resume (PDF)", type="pdf")
    jd_input = st.text_area("Target Job Description", height=300, placeholder="Paste the JD here...")
    
    if st.button("Run Strategic Audit", use_container_width=True):
        if uploaded_file and jd_input:
            with st.spinner("Analyzing signals and mirroring language..."):
                resume_text = extract_pdf_text(uploaded_file)
                output = run_ai_audit(resume_text, jd_input)
                
                if output and "DRAFT:" in output:
                    st.session_state['analysis'] = output.split("DRAFT:")[0].replace("KEYWORDS_ANALYSIS:", "").strip()
                    st.session_state['draft'] = output.split("DRAFT:")[1].strip()
                    # Identify the "To-Do" items for the checklist
                    st.session_state['todo_items'] = re.findall(r'\[(?:METRIC_NEEDED|KEYWORD_MISSING): (.*?)\]', st.session_state['draft'])
                else:
                    st.error("The AI failed to generate a draft. Please try again.")
        else:
            st.warning("Please provide both a PDF resume and a Job Description.")

# --- 5. THE AUDIT DASHBOARD ---
if 'draft' in st.session_state:
    
    col_editor, col_checklist = st.columns([1.5, 1], gap="large")

    with col_editor:
        st.subheader("✍️ Rewritten Draft (Linguistic Mirroring)")
        st.caption("Address the red [BRACKETED ITEMS] by typing your real-world data directly into the editor below.")
        # This is the heart of the tool: The user must engage with the AI's suggestions
        user_edits = st.text_area("Live Editor", value=st.session_state['draft'], height=700, label_visibility="collapsed")
        st.session_state['draft'] = user_edits

    with col_checklist:
        st.subheader("📋 Action Items Box")
        
        # Keyword Gap Analysis (Hidden in expander to focus on the To-Do list)
