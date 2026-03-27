import streamlit as st
import google.generativeai as genai
import pdfplumber, re, docx, io

# --- 1. SETUP ---
st.set_page_config(page_title="Resume Optimizer", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in Secrets.")

# --- 2. AI ENGINE (Transparency Logic) ---
def run_optimization(res_txt, jd_txt):
    # Models from your diagnostic list
    models_to_try = ['models/gemini-2.5-flash', 'models/gemini-1.5-flash', 'models/gemini-flash-latest']
    
    safe = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    prompt = f"""
    You are an elite Career Coach. Perform a strategic rewrite of this resume to align with the JD.
    
    INSTRUCTIONS:
    1. Rewrite the resume DRAFT to mirror the JD's language. Use a 'Humble but Confident' tone.
    2. Provide a detailed CHANGELOG. For every significant edit, specify:
       - [Section/Bullet]: What was changed.
       - [The Pivot]: Summary of the rewrite.
       - [The Signal]: Why this matters for this specific JD (e.g. "Mirrored 'Flywheel' keyword", "Injected ownership verb").

    FORMAT:
    CHANGELOG:
    (Your detailed list of edits and signals)
    ---
    DRAFT:
    (The full rewritten resume)

    RESUME: {res_txt}
    JD: {jd_txt}
    """
    
    last_err = ""
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            res = model.generate_content(prompt, safety_settings=safe)
            if res.text: return res.text
        except Exception as e:
            last_err = str(e)
            continue
    return f"ST_ERROR: {last_err}"

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
st.caption("Strategic Career Assistant | Beta v1.4.4")

with st.sidebar:
    st.header("1. Upload Inputs")
    f = st.file_uploader("Upload Resume (PDF)", type="pdf")
    j = st.text_area("Paste Job Description", height=300)
    
    if st.button("Begin Optimizing", use_container_width=True):
        if f and j:
            with st.spinner("Analyzing signals and documenting edits..."):
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
    # We display the Changelog as a primary insight box
    st.subheader("🛠️ Strategic Changelog")
    st.markdown("##### How I transformed your resume:")
    # We use st.markdown so the AI can use bullets and bolding in the changelog
    st.info(changelog)

    st.divider()

    col_preview, col_download = st.columns([2, 1])
    
    with col_preview:
        st.subheader("📝 Optimized Preview")
        st.code(draft, language="text")
    
    with col_download:
        st.subheader("📥 Export")
        st.write("Ready to apply? Download the clean version below.")
        st.download_button(
            label="Download Optimized Word Doc", 
            data=make_doc(draft), 
            file_name="Optimized_Resume.docx", 
            use_container_width=True
        )
        st.divider()
        st.caption("⚠️ AI Disclaimer: Verify all facts, dates, and metrics before applying.")
else:
    st.info("👋 To begin, upload your resume and the Job Description in the sidebar.")
