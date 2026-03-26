import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="centered")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in Secrets.")

# --- 2. AI ENGINE (Updated for Gemini 2.5) ---
def run_optimization(res_txt, jd_txt):
    # Updated list based on your specific API access (2.5 is now your primary)
    models_to_try = [
        'models/gemini-2.5-flash', 
        'models/gemini-1.5-flash', 
        'models/gemini-flash-latest'
    ]
    
    # Safety Bypass for Personal Information (PII)
    safe = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    prompt = f"""
    You are an elite Career Coach. 
    1. Summarize 3-4 specific tone/vocabulary pivots in a CHANGELOG.
    2. Rewrite the resume DRAFT to mirror the JD language.
    3. Tone: Humble but Confident. No extra bolding.

    FORMAT:
    CHANGELOG: (Summary of edits)
    ---
    DRAFT: (The full rewritten resume)

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    err_log = ""
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt, safety_settings=safe)
            if res.text:
                return res.text
        except Exception as e:
            err_log = str(e)
            continue
    return f"ST_ERROR: {err_log}"

def make_doc(txt):
    d = docx.Document()
    for l in txt.split('\n'):
        if l.strip():
            p = d.add_paragraph()
            # Professional bolding for names and headers
            if "|" in l or l.isupper(): p.add_run(l).bold = True
            else: p.add_run(l)
    b = io.BytesIO(); d.save(b); b.seek(0)
    return b

# --- 3. UI ---
st.title("🎯 Resume Optimizer")
st.caption("Strategic Career Assistant | Beta v1.4.3")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Begin Optimizing", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals with Gemini 2.5..."):
                try:
                    with pdfplumber.open(f) as pdf:
                        t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                    
                    out = run_optimization(t, j)
                    
                    if out and "ST_ERROR:" not in out:
                        if "---" in out:
                            p = out.split("---")
                            st.session_state['ch'] = p[0].replace("CHANGELOG:", "").strip()
                            st.session_state['dr'] = p[1].replace("DRAFT:", "").strip()
                        else:
                            st.session_state['ch'] = "Optimization complete."
                            st.session_state['dr'] = out.strip()
                    else:
                        st.error(f"AI failed. Technical Detail: {out}")
                except Exception as e:
                    st.error(f"File Error: {str(e)}")
        else:
            st.warning("Please upload a PDF and paste the JD first.")

# --- 4. DISPLAY ---
draft = st.session_state.get('dr')
changelog = st.session_state.get('ch')

if draft:
    st.subheader("🛠️ Strategic Changelog")
    st.info(changelog)

    st.subheader("📝 Optimized Preview")
    st.code(draft, language="text")
    
    st.divider()
    
    st.download_button(
        label="📥 Download Optimized Word Doc", 
        data=make_doc(draft), 
        file_name="Optimized_Resume.docx", 
        use_container_width=True
    )
    
    st.caption("⚠️ AI Disclaimer: Verify all facts and metrics before applying.")
else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
