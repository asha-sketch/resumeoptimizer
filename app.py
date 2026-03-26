import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Auditor", layout="wide")
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing API Key")

# --- 2. AI & HELPERS ---
def run_audit(res_txt, jd_txt):
    # This prompt is designed to be impossible for the AI to ignore
    prompt = f"""
    SYSTEM: You are an elite Career Coach. 
    INSTRUCTIONS:
    1. Rewrite the resume DRAFT to mirror the JD language.
    2. Tone: Humble but Confident.
    3. Use [INSERT: data] for missing metrics.
    4. Provide a 3-sentence CHANGELOG of your edits.

    OUTPUT FORMAT (MUST FOLLOW):
    CHANGELOG:
    (Your summary here)
    
    DRAFT:
    (The full rewritten resume here)

    RESUME TO EDIT: {res_txt}
    TARGET JD: {jd_txt}
    """
    for m in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt)
            if res.text and "DRAFT:" in res.text:
                return res.text
        except:
            continue
    return None

def make_doc(txt):
    d = docx.Document()
    c = re.sub(r'\[INSERT:? .*?\]', '', txt, flags=re.IGNORECASE)
    for l in c.split('\n'):
        if l.strip():
            p = d.add_paragraph()
            if "|" in l or l.isupper(): p.add_run(l).bold = True
            else: p.add_run(l)
    b = io.BytesIO(); d.save(b); b.seek(0)
    return b

# --- 3. UI ---
st.title("🎯 Resume Signal Auditor")
st.warning("⚠️ AI Disclaimer: Human judgment is required to verify all facts.")

with st.sidebar:
    st.header("1. Input")
    f = st.file_uploader("Resume (PDF)", type="pdf")
    j = st.text_area("Job Description", height=200)
    if st.button("Run Audit", use_container_width=True):
        if f and j:
            with st.spinner("Processing..."):
                with pdfplumber.open(f) as pdf:
                    t = "\n".join([pg.extract_text() for pg in pdf.pages if pg.extract_text()])
                out = run_audit(t, j)
                if out and "DRAFT:" in out:
                    # Robust splitting
                    parts = out.split("DRAFT:")
                    st.session_state['ch'] = parts[0].replace("CHANGELOG:","").strip()
                    st.session_state['dr'] = parts[1].strip()
                    st.session_state['to'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['dr'])
                else:
                    st.error("AI Error: The AI failed to format the response correctly. Please try clicking 'Run Audit' again.")

# --- 4. DASHBOARD ---
if 'dr' in st.session_state:
    with st.expander("🛠️ AI Strategy", expanded=True): st.write(st.session_state['ch'])
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("✍️ Editor")
        st.session_state['dr'] = st.text_area("e", value=st.session_state['dr'], height=500, label_visibility="collapsed")
    with c2:
        st.subheader("📋 Action Items")
        cur = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['dr'])
        dn = 0
        if st.session_state.get('to'):
            for i in st.session_state['to']:
                if i in cur: st.error(f"👉 {i}")
                else: st.success("✅ Resolved"); dn += 1
            if dn == len(st.session_state['to']):
                st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Optimized_Resume.docx", use_container_width=True)
            else: st.button(f"Locked ({dn}/{len(st.session_state['to'])})", disabled=True, use_container_width=True)
        else:
            st.success("No missing metrics detected!")
            st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Optimized_Resume.docx", use_container_width=True)
else:
    st.info("👋 Upload data in sidebar to begin.")
