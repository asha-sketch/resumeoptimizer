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
    # Using XML tags for 100% reliable parsing
    prompt = f"""
    SYSTEM: You are an elite Career Coach. 
    INSTRUCTIONS:
    1. Summarize 3 tone pivots inside <strategy> tags.
    2. Rewrite the resume inside <resume> tags. 
    3. Mirror the JD language. Tone: Humble but Confident.
    4. Use [INSERT: data] for missing metrics. No extra bolding (**).

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    for m in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt)
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
                if out:
                    # Attempt to extract text between XML tags
                    strat = re.search(r'<strategy>(.*?)</strategy>', out, re.DOTALL)
                    resm = re.search(r'<resume>(.*?)</resume>', out, re.DOTALL)
                    
                    if strat and resm:
                        st.session_state['ch'] = strat.group(1).strip()
                        st.session_state['dr'] = resm.group(1).strip()
                    else:
                        # FALLBACK: If tags aren't found, just use the raw text
                        st.session_state['ch'] = "Strategy identified by AI (Tags missing)"
                        st.session_state['dr'] = out.strip()
                    
                    st.session_state['to'] = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['dr'])
                else:
                    st.error("AI Error: Connection failed. Please try again.")

# --- 4. DASHBOARD ---
if 'dr' in st.session_state:
    with st.expander("🛠️ AI Strategy", expanded=True): st.write(st.session_state['ch'])
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("✍️ Editor")
        st.session_state['dr'] = st.text_area("e", value=st.session_state['dr'], height=600, label_visibility="collapsed")
    with c2:
        st.subheader("📋 Action Items")
        cur = re.findall(r'\[INSERT:? (.*?)\]', st.session_state['dr'])
        dn = 0
        if st.session_state.get('to'):
            for i in st.session_state['to']:
                if i in cur: st.error(f"👉 {i}")
                else: st.success("✅ Resolved"); dn += 1
            if dn == len(st.session_state['to']):
                st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Optimized.docx", use_container_width=True)
            else: st.button(f"Locked ({dn}/{len(st.session_state['to'])})", disabled=True, use_container_width=True)
        else:
            st.success("No missing metrics detected!")
            st.download_button("📥 Download", data=make_doc(st.session_state['dr']), file_name="Optimized.docx", use_container_width=True)
else:
    st.info("👋 Upload data in sidebar to begin.")
