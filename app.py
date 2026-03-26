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
    p = f"Coach. 1) Summarize 3 tone pivots in CHANGELOG. 2) Rewrite DRAFT to mirror JD. 3) Tone: Humble/Confident. 4) Use ONLY [INSERT: data] for missing metrics. 5) No extra bolding. Resume: {res_txt} JD: {jd_txt}"
    for m in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            res = genai.GenerativeModel(m).generate_content(f"CHANGELOG:\n\nDRAFT:\n\n{p}")
            if res.text: return res.text
        except: continue
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
                    st.session_state['ch'] = out.split("DRAFT:")[0].replace("CHANGELOG:","").strip()
                    st.session_state['dr'] = out.split("DRAFT:")[1].strip()
                    st.session_state['to'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['dr'])
                else: st.error("AI Error. Try again.")

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
                st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Resume.docx")
            else: st.button(f"Locked ({dn}/{len(st.session_state['to'])})", disabled=True)
        else: st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Resume.docx")
else: st.info("👋 Upload data to begin.")
