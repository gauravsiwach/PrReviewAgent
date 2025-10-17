import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Services.diff_service import (
    get_pr_details,
    get_pr_diff_summary,
    get_file_diff,
    create_sdiff_files
)
from Services.ai_input_service import build_ai_input
from Services.ai_review_service import analyze_pr_with_ai
from Services.azure_pr_comment_service import post_comments_to_azure




router = APIRouter(prefix="/pr", tags=["PR Review"])


class PRRequest(BaseModel):
    pr_id: int


@router.post("/review-pr")
async def review_pr(request: PRRequest):
    try:
        # Step 1️⃣: Get PR details
        pr_details = get_pr_details(request.pr_id)
        source_branch = pr_details.get("source_branch")
        target_branch = pr_details.get("target_branch")

        # Step 2️⃣: Get diff summary (list of files)
        diff_summary = get_pr_diff_summary(source_branch, target_branch, request.pr_id)
        files = diff_summary.get("files", [])

        # Step 3️⃣: Save all diffs into local_repo/pr_<id>/diffs/
        repo_dir = os.path.join(os.getcwd(), "local_repo", f"pr_{request.pr_id}")
        diffs_dir = os.path.join(repo_dir, "diffs")
        os.makedirs(diffs_dir, exist_ok=True)

        saved_files = []
        for f in files:
            file_path = f["filePath"]
            safe_name = file_path.replace("/", "_#").replace("\\", "_#")
            diff_file_path = os.path.join(diffs_dir, f"{safe_name}.diff")

            # Avoid duplicate write
            if os.path.exists(diff_file_path):
                os.remove(diff_file_path)

            diff_data = get_file_diff(target_branch, source_branch, file_path, request.pr_id)
            diff_text = diff_data.get("diffText", "")

            # Write diff to file
            with open(diff_file_path, "w", encoding="utf-8") as df:
                df.write(diff_text or "No diff available.")

            saved_files.append({
                "filePath": file_path,
                "diffFile": diff_file_path,
                "status": "saved" if diff_text else "empty"
            })

        # Step 4️⃣: Create sdiff folder and copy diffs
        sdiff_result = create_sdiff_files(request.pr_id)

        # Step 5️⃣: Build AI Input JSON
        ai_input = build_ai_input(pr_details)
        # print("ai_input-->", ai_input)
        ai_review = {}
 
        for file in ai_input.get("files", []):
            Ai_inpputData = {
                "title": ai_input['title'],
                "source_branch": ai_input['source_branch'],
                "target_branch": ai_input['target_branch'],
                "files_changed": ai_input['files_changed'],
                "files": [
                    {
                        "file_name": file['file_name'],   
                        "new_code": file['new_code']       
                    }
                ]
            }
                
            # as of now we are only analysis only 1 file for testing
            ai_review = analyze_pr_with_ai(Ai_inpputData)
            # Step 5️⃣ (continued): Post AI comments to Azure PR
            azure_result = post_comments_to_azure(request.pr_id, ai_review, ai_review.get("filePath"))
            # break

            
        # Step 6️⃣: Return full response
        return {
            "message": "PR diff summary, sdiff, and AI input generated successfully",
            "data": {
                "pr_id": pr_details.get("pr_id"),
                "title": pr_details.get("title"),
                "source_branch": source_branch,
                "target_branch": target_branch,
                # "diff_summary": diff_summary,
                # "saved_diffs": saved_files,
                # "sdiff": sdiff_result,
                # "ai_input": ai_input,       
                # "ai_review": ai_review,
                "azure_result": azure_result 
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
