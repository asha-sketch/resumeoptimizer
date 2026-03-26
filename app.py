import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="wide")
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key in Streamlit Secrets")

# --- 2. AI LOGIC (Safety Filters Disabled) ---
def run_optimization(res_txt, jd_txt):
    # Models from your previous diagnostic
    models = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash', 'models/gemini-flash-latest']
    
    # This prevents Google from blocking the resume due to contact info
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    prompt = f"""
    You are an elite Career Coach. 
    Rewrite the provided resume to mirror the language of the Job Description.
    Tone: Humble but Confident. No extra bolding.
    
    FORMAT:
    Put the rewritten resume inside <resume> tags.
    Put 5 strategic suggestions inside <suggestions> tags.

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    last_err = ""
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            # Call with safety settings
            res = model.generate_content(prompt, safety_settings=safety_settings)
            if res.text:
                return res.text
        except Exception as e:
            last_err = str(e)
            continue
    return f"ERROR: {last_err}"

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
st.title("🚀 Resume Signal Optimizer")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Optimize & Suggest", use_container_width=True):
        if f and j:
            with st.spinner("Gemini is thinking..."):
                with pdfplumber.open(f) as pdf:
                    t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                out = run_optimization(t, j)
                
                if out and "ERROR:" not in out:
                    # Robust parsing with Fallbacks
                    res_match = re.search(r'<resume>(.*?)</resume>', out, re.S)
                    sug_match = re.search(r'<suggestions>(.*?)</suggestions>', out, re.S)
                    
                    if res_match:
                        st.session_state['dr'] = res_match.group(1).strip()
                        st.session_state['sg'] = sug_match.group(1).strip() if sug_match else "No suggestions found."
                    else:
                        # If AI forgot tags, use raw text
                        st.session_state['dr'] = out.strip()
                        st.session_state['sg'] = "Note: AI formatted response as raw text."
                else:
                    st.error(f"AI Failed: {out}")

# --- 4. DASHBOARD ---
if 'dr' in st.session_state:
    c1, c2 = st.columns([2, 1], gap="large")

    with c1:
        st.subheader("✍️ Rewritten Resume")
        st.session_state['dr'] = st.text_area("Resume Editor", value=st.session_state['dr'], height=600, label_visibility="collapsed")
        st.download_button("📥 Download Word Doc", data=make_doc(st.session_state['dr']), file_name="Optimized_Resume.docx", use_container_width=True)

    with c2:
        st.subheader("💡 Strategic Suggestions")
        st.markdown(st.session_state['sg'])
        st.divider()
        st.caption("⚠️ Disclaimer: Factual accuracy is your responsibility.")
else:
    st.info("👋 Upload your resume and the Job Description in the sidebar to begin.")
