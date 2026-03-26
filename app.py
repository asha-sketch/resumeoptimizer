import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="wide")
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key")

# --- 2. AI LOGIC (Clean & Simple) ---
def run_optimization(res_txt, jd_txt):
    # Using your confirmed working models
    models = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    prompt = f"""
    You are an elite Career Coach. 
    1. Rewrite the resume inside <resume> tags. 
    2. Use a 'Humble but Confident' tone and mirror the JD language.
    3. Retain the original structure. No extra bolding (**).
    4. Provide 5-7 optional 'Next Level' suggestions for the user inside <suggestions> tags. 
       These should be specific things they could add (e.g. "Add a metric for X" or "Explain the scale of Y").

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt)
            if res.text: return res.text
        except: continue
    return None

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
st.caption("Simplified Beta: Rewrite & Strategic Suggestions")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Optimize & Suggest", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals..."):
                with pdfplumber.open(f) as pdf:
                    t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                out = run_optimization(t, j)
                if out:
                    # Parse the two sections
                    st.session_state['dr'] = re.search(r'<resume>(.*?)</resume>', out, re.S).group(1).strip() if '<resume>' in out else out.strip()
                    st.session_state['sg'] = re.search(r'<suggestions>(.*?)</suggestions>', out, re.S).group(1).strip() if '<suggestions>' in out else "Check the draft for improvements."
                else: st.error("AI Error. Please try again.")

# --- 4. DASHBOARD ---
if 'dr' in st.session_state:
    c1, c2 = st.columns([2, 1], gap="large")

    with c1:
        st.subheader("✍️ Rewritten Resume")
        st.info("💡 You can edit this text directly before downloading.")
        # Main Editor
        st.session_state['dr'] = st.text_area("Resume Editor", value=st.session_state['dr'], height=700, label_visibility="collapsed")
        
        st.divider()
        st.download_button(
            label="📥 Download Optimized Word Doc", 
            data=make_doc(st.session_state['dr']), 
            file_name="Optimized_Resume.docx", 
            use_container_width=True
        )

    with c2:
        st.subheader("💡 Strategic Suggestions")
        st.write("Use these to strengthen the resume further:")
        # Display suggestions as a clean list
        st.markdown(st.session_state['sg'])
        
        st.divider()
        st.caption("⚠️ AI Disclaimer: This rewrite is a draft. Please verify all facts and dates before applying.")

else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
