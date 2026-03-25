# --- Updated AI Function for Google (Copy and replace this part) ---

def get_ai_rewrite(resume_text, jd_text):
    try:
        # We use 'gemini-1.5-flash' - if this fails, we try 'gemini-pro'
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        You are an elite Career Coach. Optimize this resume for the provided Job Description (JD).
        
        TONE: Humble but Confident. No 'visionary' or 'rockstar' talk. Use ownership verbs.
        STRATEGY: 
        1. Identify 8 high-signal keywords from the JD.
        2. Rewrite the resume to show 'Staff-level' impact (flywheels, strategy, cross-functional).
        3. Insert [ACTION: ...] for missing metrics and [QUERY: ...] for fact-checks.
        
        RESUME: {resume_text}
        JD: {jd_text}
        
        IMPORTANT: Start your response with 'KEYWORDS:' followed by the list. 
        Then write 'DRAFT:' followed by the full rewritten resume.
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # This will show you the REAL error message on your website
        st.error(f"Google AI Error: {str(e)}")
        return None
