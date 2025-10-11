import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

AZURE_ORG = os.getenv("AZURE_ORG")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")
AZURE_REPO_ID = os.getenv("AZURE_REPO_ID")
AZURE_PAT = os.getenv("AZURE_PAT")

def encode_pat(pat: str):
    token_bytes = f":{pat}".encode("ascii")
    return base64.b64encode(token_bytes).decode("ascii")

def post_comments_to_azure(pr_id: int, ai_review: dict, file_path: str):
    """Posts AI-generated comments to Azure DevOps PR inline"""
    url = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/git/repositories/{AZURE_REPO_ID}/pullRequests/{pr_id}/threads?api-version=7.1"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encode_pat(AZURE_PAT)}"
    }

    comments = ai_review.get("comments", [])
    posted_results = []

    for c in comments:
        line_number = c.get("line_number")
        comment_text = c.get("comment")
        line_hint = c.get("line_hint")

        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": f"💬 **AI Suggestion ({line_hint}):** {comment_text}",
                    "commentType": 1
                }
            ],
            "status": "active",
            "threadContext": {
                "filePath": file_path,
                "rightFileStart": {"line": line_number, "offset": 1},
                "rightFileEnd": {"line": line_number, "offset": 1},
                "leftFileStart": {"line": line_number, "offset": 1},
                "leftFileEnd": {"line": line_number, "offset": 1}
            }
        }


        response = requests.post(url, headers=headers, json=payload)
        result = {
            "line_hint": line_hint,
            "line_number": line_number,
            "status": "✅ Posted" if response.status_code in [200, 201] else f"❌ {response.text}"
        }
        posted_results.append(result)

    return {"total_comments": len(posted_results), "results": posted_results}
