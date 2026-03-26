import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="centered")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in Secrets.")

# --- 2. AI ENGINE (High Stability) ---
def run_optimization(res_txt, jd_txt):
    # Trying the most common stable models
    models_to_try = ['models/gemini-1.5-flash', 'models/gemini-2.0-flash']
    
    # Complete Safety Bypass: Resumes often trigger 'Personal Information' blocks
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    prompt = f"""
    You are an elite Career Coach. 
    
    1. Rewrite the resume for the provided JD. 
    2. Use a 'Humble but Confident' tone. 
    3. Categorize your edits in a CHANGELOG.
    
    FORMAT:
    CHANGELOG: (Summary of edits)
    ---
    DRAFT: (The full rewritten resume)

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    last_error = "Unknown Error"
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt, safety_settings=safety_settings)
            if res.text:
                return res.text
        except Exception as e:
            last_error = str(e)
            continue
    return f"ST_ERROR: {last_error}"

def make_doc(txt):
    d = docx.Document()
    for l in txt.split('\n'):
        if l.strip():
            p = d.add_paragraph()
            if "|" in l or l.isupper(): p.add_run(l).bold = True
            else: p.add_run(l)
    b = io.BytesIO(); d.save(b); b.seek(0)
    return b

# --- 3. UI ---
st.title("🎯 Resume Optimizer")
st.caption("Strategic Career Assistant | Beta v1.4.2")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Begin Optimizing", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals..."):
                try:
                    with pdfplumber.open(f) as pdf:
                        t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                    
                    out = run_optimization(t, j)
                    
                    if out and "ST_ERROR:" not in out:
                        if "---" in out:
                            parts = out.split("---")
                            st.session_state['ch'] = parts[0].replace("CHANGELOG:", "").strip()
                            st.session_state['dr'] = parts[1].replace("DRAFT:", "").strip()
                        else:
                            st.session_state['ch'] = "Strategy identified."
                            st.session_state['dr'] = out.strip()
                    else:
                        st.error(f"AI Failed. Technical Detail: {out}")
                except Exception as e:
                    st.error(f"File Error: {str(e)}")
        else:
            st.warning("Please upload a PDF and paste the JD first.")

# --- 4. DISPLAY RESULTS ---
draft = st.session_state.get('dr')
changelog = st.session_state.get('ch')

if draft:
    st.subheader("🛠️ Strategic Changelog")
    st.info(changelog)

    st.subheader("📝 Optimized Preview")
    # Using a code block makes it look clean and professional
    st.code(draft, language="text")
    
    st.divider()
    
    st.download_button(
        label="📥 Download Optimized Word Doc", 
        data=make_doc(draft), 
        file_name="Optimized_Resume.docx", 
        use_container_width=True
    )
    
    st.caption("⚠️ AI Disclaimer: Factual accuracy is the user's responsibility. Falsifying metrics is not recommended.")
else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
