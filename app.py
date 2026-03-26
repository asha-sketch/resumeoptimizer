import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="centered")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in Secrets.")

# --- 2. AI ENGINE ---
def run_optimization(res_txt, jd_txt):
    # Using the most reliable model names
    models = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    prompt = f"""
    You are an elite Career Coach. Rewrite this resume for this JD.
    Tone: Humble but Confident. 
    
    REQUIRED OUTPUT FORMAT:
    CHANGELOG:
    - [Categorized summary of edits: Keyword Matching, Strategic Positioning, etc.]
    - [Count of major sentence edits]
    
    ---
    
    DRAFT:
    [The full rewritten resume in plain text. Mirror original formatting. No bolding.]

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            # Safety settings to prevent blocking
            safe = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}]
            res = model.generate_content(prompt, safety_settings=safe)
            if res.text: return res.text
        except: continue
    return None

def make_doc(txt):
    d = docx.Document()
    for l in txt.split('\n'):
        if l.strip():
            p = d.add_paragraph()
            # Professional bolding for headers
            if "|" in l or l.isupper(): p.add_run(l).bold = True
            else: p.add_run(l)
    b = io.BytesIO(); d.save(b); b.seek(0)
    return b

# --- 3. UI ---
st.title("🎯 Resume Optimizer")
st.caption("Strategic Career Assistant | Beta")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Begin Optimizing", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals..."):
                with pdfplumber.open(f) as pdf:
                    t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                out = run_optimization(t, j)
                
                if out:
                    # Simple split on the separator '---'
                    if "---" in out:
                        parts = out.split("---")
                        st.session_state['ch'] = parts[0].replace("CHANGELOG:", "").strip()
                        st.session_state['dr'] = parts[1].replace("DRAFT:", "").strip()
                    else:
                        st.session_state['ch'] = "Optimization completed."
                        st.session_state['dr'] = out.strip()
                else:
                    st.error("AI Error. Please try again.")

# --- 4. DISPLAY RESULTS ---
# We use .get() to prevent the KeyError you saw earlier
draft = st.session_state.get('dr')
changelog = st.session_state.get('ch')

if draft:
    st.subheader("🛠️ Strategic Changelog")
    st.info(changelog)

    st.subheader("📝 Optimized Preview")
    # Displaying as read-only markdown for clarity
    st.markdown(f"```\n{draft}\n```")
    
    st.divider()
    
    # Simple Download Button
    st.download_button(
        label="📥 Download Optimized Word Doc", 
        data=make_doc(draft), 
        file_name="Optimized_Resume.docx", 
        use_container_width=True
    )
    
    st.caption("⚠️ AI Disclaimer: This output is AI-generated. Factual accuracy is the user's responsibility.")
else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
