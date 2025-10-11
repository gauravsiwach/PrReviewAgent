import os
import json

def build_ai_input(pr_details: dict):
    """
    Build structured AI input JSON from cleaned diff files in /local_repo/sdiff/.
    Extracts correct original file names from encoded pattern (_# => /)
    """
    base_dir = os.path.join(os.getcwd(), "local_repo", "sdiff")
    pr_id = pr_details.get("pr_id")
    ai_files = []

    for filename in sorted(os.listdir(base_dir)):
        # Example: pr_15_src_#features_#RecommendedMenus_#index.jsx.diff
        if filename.startswith(f"pr_{pr_id}_") and filename.endswith(".diff"):
            file_path = os.path.join(base_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                new_code = f.read().strip()

            # Clean filename for AI readability & mapping
            clean_name = (
                filename
                .replace(f"pr_{pr_id}_", "")   # remove PR prefix
                .replace(".diff", "")           # remove extension
                .replace("_#", "/")             # restore folder structure
            )

            ai_files.append({
                "file_name": "/" + clean_name,        # e.g., src/features/RecommendedMenus/index.jsx ✅
                "new_code": new_code
            })
            result = []
            result.append(ai_files[0])

    ai_input = {
        "pr_id": pr_id,
        "title": pr_details.get("title"),
        "source_branch": pr_details.get("source_branch"),
        "target_branch": pr_details.get("target_branch"),
        "files_changed": len(result), #len(ai_files),
        "files": result #ai_files
    }

    return ai_input
