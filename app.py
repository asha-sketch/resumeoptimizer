import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP & BRANDING ---
st.set_page_config(page_title="Resume Optimizer", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stTextArea textarea { font-family: 'Arial', sans-serif; font-size: 14px; line-height: 1.6; }
    .highlight-text { background-color: #e8f0fe; padding: 10px; border-radius: 5px; border-left: 5px solid #4285f4; }
    </style>
    """, unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key in Secrets.")

# --- 2. AI LOGIC (Categorized Audit) ---
def run_optimization(res_txt, jd_txt):
    models = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    prompt = f"""
    You are an elite Career Coach. Perform a high-impact rewrite of the provided resume.
    
    TASK:
    1. Rewrite the resume to mirror the JD's language. Use a 'Humble but Confident' tone.
    2. Provide a CHANGELOG: Categorize changes (e.g., Keyword Matching, Strategic Positioning, Metric Enhancement). 
    3. Specify how many major sentence edits were made.
    
    FORMAT:
    - Put the Changelog & Count inside <changelog> tags.
    - Put a version of the resume with changed phrases **bolded** inside <preview> tags.
    - Put the clean, unbolded rewritten resume inside <resume> tags.
    - Put 5 strategic suggestions inside <suggestions> tags.

    RESUME: {res_txt}
    JD: {jd_text}
    """
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt, safety_settings=safety_settings)
            if res.text: return res.text
        except Exception: continue
    return None

def make_doc(txt):
    d = docx.Document()
    for l in txt.split('\n'):
        if l.strip():
            p = d.add_paragraph()
            # Bolding logic for headers in Word
            if "|" in l or l.isupper(): p.add_run(l).bold = True
            else: p.add_run(l)
    b = io.BytesIO(); d.save(b); b.seek(0)
    return b

# --- 3. UI ---
st.title("🎯 Resume Optimizer")
st.caption("Strategic Career Assistant | Beta v1.4.0")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Begin Optimizing", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals and rewriting..."):
                with pdfplumber.open(f) as pdf:
                    t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                out = run_optimization(t, j)
                
                if out:
                    # Parsing
                    st.session_state['ch'] = re.search(r'<changelog>(.*?)</changelog>', out, re.S).group(1).strip() if '<changelog>' in out else "Summary unavailable."
                    st.session_state['pv'] = re.search(r'<preview>(.*?)</preview>', out, re.S).group(1).strip() if '<preview>' in out else "Preview unavailable."
                    st.session_state['dr'] = re.search(r'<resume>(.*?)</resume>', out, re.S).group(1).strip() if '<resume>' in out else out.strip()
                    st.session_state['sg'] = re.search(r'<suggestions>(.*?)</suggestions>', out, re.S).group(1).strip() if '<suggestions>' in out else "No suggestions."
                else: st.error("AI Error. Please try again.")

# --- 4. DASHBOARD ---
if 'dr' in st.session_state:
    
    # Changelog Summary
    st.subheader("🛠️ Optimization Summary")
    st.info(st.session_state['ch'])

    col_ed, col_sug = st.columns([2, 1], gap="large")

    with col_ed:
        st.subheader("✍️ Review & Edit")
        
        # Visual Preview with Highlights
        with st.expander("👁️ View Highlighted Changes (Read-Only)", expanded=True):
            st.markdown(st.session_state['pv'])
        
        st.write("---")
        st.caption("Final Editor: Tweak the text below before downloading.")
        st.session_state['dr'] = st.text_area("Final Clean Text", value=st.session_state['dr'], height=600, label_visibility="collapsed")
        
        st.divider()
        st.download_button("📥 Download Optimized Word Doc", data=make_doc(st.session_state['dr']), file_name="Optimized_Resume.docx", use_container_width=True)

    with col_sug:
        st.subheader("💡 Strategic Suggestions")
        st.write("Ways to further bolster your impact:")
        st.markdown(st.session_state['sg'])
        
        st.divider()
        st.caption("⚠️ AI Disclaimer: Factual accuracy and date verification remain the user's responsibility.")

else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
