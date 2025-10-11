import os
import base64
import requests
import subprocess
import re
from dotenv import load_dotenv

load_dotenv()

AZURE_ORG = os.getenv("AZURE_ORG")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")
AZURE_REPO_ID = os.getenv("AZURE_REPO_ID")
AZURE_PAT = os.getenv("AZURE_PAT")


def encode_pat(pat: str) -> str:
    token_bytes = f":{pat}".encode("ascii")
    return base64.b64encode(token_bytes).decode("ascii")


# =========================================================
# 🔹 Step 1: Get PR metadata
# =========================================================
def get_pr_details(pr_id: int):
    try:
        url = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/git/repositories/{AZURE_REPO_ID}/pullRequests/{pr_id}?api-version=7.1"
        headers = {"Authorization": f"Basic {encode_pat(AZURE_PAT)}", "Content-Type": "application/json"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        pr_data = response.json()

        source_branch = pr_data.get("sourceRefName", "").replace("refs/heads/", "")
        target_branch = pr_data.get("targetRefName", "").replace("refs/heads/", "")

        return {
            "pr_id": pr_data.get("pullRequestId"),
            "title": pr_data.get("title"),
            "source_branch": source_branch,
            "target_branch": target_branch
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch PR details: {e}"}


# =========================================================
# 🔹 Step 2: Local Git Diff (Lightweight Summary)
# =========================================================
def get_git_diff(base_branch: str, feature_branch: str, pr_id: int = None):
    """Get changed React-related files & git diff command."""
    repo_root = os.path.join(os.getcwd(), "local_repo")
    os.makedirs(repo_root, exist_ok=True)
    repo_dir = os.path.join(repo_root, f"pr_{pr_id or 'temp'}")
    repo_url = f"https://{AZURE_PAT}@dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_git/{AZURE_REPO_ID}"

    try:
        # Step 1️⃣: Clone or fetch repo
        if not os.path.exists(repo_dir):
            subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        else:
            subprocess.run(["git", "-C", repo_dir, "fetch", "origin"], check=True)

        # Step 2️⃣: Fetch branches
        subprocess.run(["git", "-C", repo_dir, "fetch", "origin", base_branch, feature_branch], check=True)

        # Step 3️⃣: Get changed files (React-only)
        result = subprocess.run(
            ["git", "-C", repo_dir, "diff", "--name-only", f"origin/{base_branch}", f"origin/{feature_branch}"],
            capture_output=True, text=True, check=True
        )

        changed_files = [
            f for f in result.stdout.splitlines()
            if f.endswith((".js", ".jsx", ".ts", ".tsx"))
        ]

        return {
            "source": feature_branch,
            "target": base_branch,
            "totalFiles": len(changed_files),
            "files": [
                {
                    "filePath": f,
                    "changeType": "modified",
                    "diffCommand": f"git diff origin/{base_branch} origin/{feature_branch} -- {f}"
                }
                for f in changed_files
            ]
        }

    except subprocess.CalledProcessError as e:
        print(f"❌ Git diff failed:\n{e.stderr or e.stdout}")
        return None


# =========================================================
# 🔹 Step 3: Get single file diff (Only new added code)
# =========================================================
def get_file_diff(base_branch: str, feature_branch: str, file_path: str, pr_id: int):
    """Return diff for a specific file with line numbers for new code."""
    repo_dir = os.path.join(os.getcwd(), "local_repo", f"pr_{pr_id}")
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "diff", "--unified=5", f"origin/{base_branch}", f"origin/{feature_branch}", "--", file_path],
            capture_output=True,
            text=True,
            check=True
        )

        diff_text = result.stdout.strip()
        if not diff_text:
            return {"filePath": file_path, "diffText": ""}

        numbered_lines = []
        current_line_num = 0

        for line in diff_text.splitlines():
            # skip headers and metadata
            if line.startswith(("diff --git", "index ", "--- ", "+++ ")):
                continue

            if line.startswith("@@"):
                # extract line number from diff hunk header
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line_num = int(match.group(1)) - 1
                continue

            # update line number counter
            current_line_num += 1

            # clean up and add line number
            if line.startswith("+") and not line.startswith("+++"):
                code_line = line[1:]
                numbered_lines.append(f"{current_line_num:04d}: {code_line}")
            elif not line.startswith("-"):  # keep context lines
                code_line = line[1:] if line.startswith(" ") else line
                numbered_lines.append(f"{current_line_num:04d}: {code_line}")

        clean_code = "\n".join(numbered_lines).strip()
        return {"filePath": file_path, "diffText": clean_code}

    except subprocess.CalledProcessError as e:
        return {"error": f"Git diff failed for {file_path}: {e.stderr or e.stdout}"}


# =========================================================
# 🔹 Step 4: Azure API fallback
# =========================================================
def get_pr_diff_summary_via_api(source_branch: str, target_branch: str):
    """Fallback if Git diff fails."""
    def fetch_branch_heads():
        refs_url = (
            f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/git/repositories/"
            f"{AZURE_REPO_ID}/refs?filter=heads/&api-version=7.1"
        )
        headers = {"Authorization": f"Basic {encode_pat(AZURE_PAT)}"}
        resp = requests.get(refs_url, headers=headers)
        refs = resp.json().get("value", [])
        return {r["name"].replace("refs/heads/", ""): r["objectId"] for r in refs}

    branch_heads = fetch_branch_heads()
    base_commit = branch_heads.get(target_branch)
    target_commit = branch_heads.get(source_branch)

    if not base_commit or not target_commit:
        return {"error": "Commit IDs not found."}
    return {"source": source_branch, "target": target_branch, "files": []}


# =========================================================
# 🔹 Step 5: Unified entry point
# =========================================================
def get_pr_diff_summary(source_branch: str, target_branch: str, pr_id: int = None):
    diff_summary = get_git_diff(target_branch, source_branch, pr_id)
    if diff_summary:
        return diff_summary
    print("⚠️ Falling back to Azure API diff.")
    return get_pr_diff_summary_via_api(source_branch, target_branch)

# =========================================================
# 🔹 Step 6: Save all file diffs
# =========================================================
# def save_all_file_diffs(pr_id: int, source_branch: str, target_branch: str, files: list):
#     """
#     Fetch diff for each file and save as individual .diff files.
#     Returns summary with file paths and saved locations.
#     """
#     repo_dir = os.path.join(os.getcwd(), "local_repo", f"pr_{pr_id}")
#     diffs_dir = os.path.join(repo_dir, "diffs")
#     os.makedirs(diffs_dir, exist_ok=True)

#     saved_diffs = []

#     for file in files:
#         file_path = file["filePath"]
#         safe_name = file_path.replace("/", "_").replace("\\", "_")
#         diff_file_path = os.path.join(diffs_dir, f"{safe_name}.diff")

#         diff_data = get_file_diff(target_branch, source_branch, file_path, pr_id)
#         diff_text = diff_data.get("diffText", "")

#         # Write to file
#         with open(diff_file_path, "w", encoding="utf-8") as f:
#             f.write(diff_text or "No diff available.")

#         saved_diffs.append({
#             "filePath": file_path,
#             "diffFile": diff_file_path,
#             "status": "saved" if diff_text else "empty"
#         })

#     print(f"✅ All diffs saved in: {diffs_dir}")
#     return {"totalFiles": len(saved_diffs), "saved": saved_diffs}

# =========================================================
# 🔹 Step 7: Create sdiff folder and copy all file diffs
# =========================================================
def create_sdiff_files(pr_id: int):
    """
    Create a /local_repo/sdiff folder (if not exists),
    and copy each .diff from local_repo/pr_<id>/diffs/
    into /local_repo/sdiff/ as pr_<id>_<filename>.diff
    """
    base_dir = os.path.join(os.getcwd(), "local_repo")
    source_diffs_dir = os.path.join(base_dir, f"pr_{pr_id}", "diffs")
    sdiff_dir = os.path.join(base_dir, "sdiff")
    os.makedirs(sdiff_dir, exist_ok=True)

    if not os.path.exists(source_diffs_dir):
        return {"error": f"No diffs found for PR {pr_id} in {source_diffs_dir}"}

    created_files = []

    for filename in sorted(os.listdir(source_diffs_dir)):
        if filename.endswith(".diff"):
            src_path = os.path.join(source_diffs_dir, filename)
            dest_filename = f"pr_{pr_id}_{filename}"
            dest_path = os.path.join(sdiff_dir, dest_filename)

            with open(src_path, "r", encoding="utf-8") as src, \
                 open(dest_path, "w", encoding="utf-8") as dest:
                dest.write(f"# Diff for PR {pr_id}: {filename.replace('.diff', '')}\n\n")
                dest.write(src.read())

            created_files.append(dest_path)

    print(f"✅ {len(created_files)} sdiff files created in: {sdiff_dir}")
    return {"sdiffDir": sdiff_dir, "files": created_files}
