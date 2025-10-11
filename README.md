# PR Review Agent

## Overview
PR Review Agent is a FastAPI-based application that automates Pull Request (PR) reviews for React/JavaScript projects integrated with Azure DevOps. It fetches PR data, extracts diffs, generates AI-powered code reviews using OpenAI, and optionally posts comments back to Azure DevOps.

## Features
- **PR Data Extraction**: Fetches PR details, commits, and file changes from Azure DevOps.
- **Git Diff Analysis**: Uses local Git operations to identify changed React files.
- **AI Code Review**: Leverages OpenAI GPT models to provide structured code reviews with scores, issues, and recommendations.
- **File Management**: Saves diffs to local directories for processing and analysis.
- **Azure Integration**: Posts AI-generated comments directly to PRs in Azure DevOps.

## Prerequisites
- Python 3.8+
- Azure DevOps account with a Personal Access Token (PAT).
- OpenAI API key.
- Git installed on your system.

## Installation
1. Clone the repository:
   ```
   git clone <your-repo-url>
   cd PrReviewAgent
   ```

2. Install dependencies:
   ```
   pip install fastapi uvicorn python-dotenv requests openai pydantic
   ```

3. Set up environment variables:
   - Create a `.env` file in the project root:
     ```
     AZURE_ORG=your_azure_org
     AZURE_PROJECT=your_azure_project
     AZURE_REPO_ID=your_azure_repo_id
     AZURE_PAT=your_azure_pat
     OPENAI_API_KEY=your_openai_api_key
     ```
   - Ensure `.env` is in `.gitignore` for security.

## Usage
1. Run the application:
   ```
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Make a POST request to `/review-pr`:
   - Endpoint: `http://localhost:8000/pr/review-pr`
   - Body:
     ```
     {
       "pr_id": 15
     }
     ```
   - Response: Includes PR details, diff summary, AI review, and Azure comments.

3. Optional: Fetch single file diffs at `/review-pr/file-diff?pr_id=15&file_path=src/ApolloProvider.jsx`.

## Project Structure
- `main.py`: FastAPI app setup and health check.
- `Route/pr_review.py`: API endpoints for PR review.
- `Services/`:
  - `diff_service.py`: Git diff extraction and file handling.
  - `ai_input_service.py`: Builds input for AI analysis.
  - `ai_review_service.py`: Integrates with OpenAI for code reviews.
  - `azure_pr_comment_service.py`: Posts comments to Azure DevOps.
- `.env`: Environment variables.
- `.gitignore`: Excludes sensitive files.

## Configuration
- **Azure DevOps**: Ensure PAT has Code Read and Write scopes.
- **OpenAI**: Use a model like `gpt-4o-mini` for cost efficiency.
- **File Naming**: Uses `_#` for separators in diff files.

## Troubleshooting
- **Duplication Issues**: Ensure consistent file naming and clean up `local_repo/sdiff/`.
- **Errors**: Check logs for Azure API failures or OpenAI rate limits.

## Contributing
- Fork the repo, make changes, and submit a PR.
- Follow Python best practices and add tests for new features.

## License
- MIT License.
