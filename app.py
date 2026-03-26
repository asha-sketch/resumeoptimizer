import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
from docx import Document
from io import BytesIO

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Auditor", layout="wide")
st.markdown("<style>.stTextArea textarea { font-family: Arial; font-size: 14px; }</style>", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in Secrets.")

# --- 2. AI BRAIN ---
def run_ai_audit(resume_text, jd_text):
    models = ['gemini-2.0-flash', 'gemini-1.5-flash']
    prompt = f"""
    You are a Career Coach. 1) Summarize 3 tone pivots in CHANGELOG. 
    2) Rewrite resume DRAFT to mirror JD language. 
    3) Tone: Humble but Confident. 
    4) Use ONLY [INSERT: specific data] for missing metrics. 
    5) RETAIN original structure. No extra bolding (**).

    FORMAT:
    CHANGELOG: (Summary)
    DRAFT: (Full resume)

    RESUME: {resume_text}
    JD: {jd_text}
    """
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt)
            if res.text: return res.text
        except: continue
    return None

# --- 3. HELPERS ---
def create_docx(text):
    doc = Document()
    clean = re.sub(r'\[INSERT:? .*?\]', '', text, flags=re.IGNORECASE) 
    for line in clean.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            if "|" in line or line.isupper(): p.add_run(line).bold = True
            else: p.add_run(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. UI ---
st.title("🎯 Resume Signal Auditor")
st.warning("⚠️ AI Disclaimer: This tool is an assistant. Human judgment is required to verify all facts.")

with st.sidebar:
    st.header("1. Input Data")
    u_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    jd_in = st.text_area("Target Job Description", height=250)
    if st.button("Run Strategic Audit", use_container_width=True):
        if u_file and jd_in:
            with st.spinner("Auditing..."):
                with pdfplumber.open(u_file) as pdf:
                    r_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                out = run_ai_audit(r_text, jd_in)
                if out and "DRAFT:" in out:
                    st.session_state['changelog'] = out.split("DRAFT:")[0].replace("CHANGELOG:", "").strip()
                    st.session_state['draft'] = out.split("DRAFT:")[1].strip()
                    st.session_state['todo'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['draft'])
                else: st.error("AI Error. Please try again.")

# --- 5. DASHBOARD ---
if 'draft' in st.session_state:
    with st.expander("🛠️ AI Strategy", expanded=True):
        st.write(st.session_state['changelog'])

    ed_col, ch_col = st.columns([2, 1], gap="large")
    with ed_col:
        st.subheader("✍️ Draft & Editor")
        st.session_state['draft'] = st.text_area("Content", value=st.session_state['draft'], height=600, label_visibility="collapsed")

    with ch_col:
        st.subheader("📋 Action Items")
        curr_tags = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['draft'])
        done = 0
        if st.session_state.get('todo'):
            for item in st.session_state['todo']:
                if item in curr_tags: st.error(f"👉 {item}")
                else:
                    st.success("✅ Resolved")
                    done += 1
            if done == len(st.session_state['todo']):
                st.balloons()
                st.download_button("📥 Download .docx", data=create_docx(st.session_state['draft']), file_name="Optimized.docx", use_container_width=True)
            else: st.button(f"Locked ({done}/{len(st.session_state['todo'])})", disabled=True, use_container_width=True)
        else:
            st.success("Draft ready!")
            st.download_button("📥 Download .docx", data=create_
