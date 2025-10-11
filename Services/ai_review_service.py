import os
import json
from openai import OpenAI

# ✅ Initialize client once (no openai.api_key needed here)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_pr_with_ai(ai_input: dict):
    """
    Analyze PR changes using OpenAI GPT model.
    Returns a structured summary, score, and suggestions.
    """
    try:
        files = ai_input.get("files", [])
        first_file = files[0] if files else None
        files_text = ""

        if first_file:
            files_text = f"### {first_file['file_name']}\n{first_file['new_code']}"
        else:
            print("⚠️ No file found in ai_input")

    except Exception as e:
        print("❌ Error reading files -->", e)
        return {"error": f"Error reading files: {e}"}

    print("analyze_pr_with_ai: File content loaded successfully")

    # 🧠 Build the AI prompt
    SYSTEM_PROMPT = f"""
    You are a **senior front-end software engineer and expert React code reviewer**. 
Your job is to perform a detailed technical review of the provided code changes.

Focus your review on:
1. **Code Readability** – clarity, naming, formatting, indentation.
2. **Maintainability** – modularity, structure, reusability.
3. **Code Duplication** – repeated patterns or redundant logic.
4. **Best Practices** – React, JS/TS, and general software design principles.
5. **Potential Bugs or Anti-patterns** – logic errors, unsafe assumptions, or missing validations.
6. **Performance Considerations** – unnecessary re-renders, API inefficiencies, large computations.

Your task:
- Identify issues and provide specific recommendations.
- Additionally, write short PR-style comments for specific code snippets or identifiers related to each issue.

You must respond **ONLY** in valid JSON format like this:

    {{
  "filePath": "/src/features/RecommendedMenus/index.jsx",    
  "summary": "Brief overall summary of the code review",
  "issues": [
    
    "Issue 1 with explanation and suggested fix",
    "Issue 2 with explanation and suggested fix",
    "Issue 3 ..."
  ],
  "recommendations": [
    "Recommendation 1 to improve code",
    "Recommendation 2 to enhance maintainability"
  ],
  "comments": [
    {{
      "line_number": 45,
      "line_hint": "Relevant code identifier or variable name (e.g., 'localStorage.getItem', 'split(...)', 'apiLink')",
      "comment": "A short, professional PR comment that could be added directly on that line."
    }}
  ],
  "code_quality_score": 1-10
}}

PR Title: {ai_input['title']}
Source Branch: {ai_input['source_branch']}
Target Branch: {ai_input['target_branch']}
Files Changed: {ai_input['files_changed']}

Return ONLY valid JSON. No extra text or explanation.
    
    """

    print("🧠 Sending prompt to OpenAI model...")

    code = f"""Code Changes:    {files_text}"""

    try:
        # ✅ Correct call for openai>=1.x
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # ⚡ fast and cheaper than gpt-4
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},       
                {"role": "user", "content": code}
                ],
            temperature=0.3,
            max_tokens=700
        )

        # ✅ Access message content correctly for new SDK
        content = response.choices[0].message.content.strip()

        # ✅ Try parsing the model's response into JSON
        try:
            parsed = json.loads(content)
            print("✅ AI response parsed successfully")
            # print("parsed-->", parsed)
            return parsed
        except json.JSONDecodeError:
            print("⚠️ AI did not return valid JSON")
            return {"raw_output": content, "error": "Model response not in JSON format"}

    except Exception as e:
        print("❌ analyze_pr_with_ai error -->", e)
        return {"error": f"AI review failed: {str(e)}"}
