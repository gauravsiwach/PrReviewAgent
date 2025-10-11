from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Route import pr_review   # 👈 folder name should be lowercase

app = FastAPI(title="AI PR Review Agent")

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],      # Allows all HTTP methods
    allow_headers=["*"],      # Allows all headers
)

# ✅ Health-check route
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ✅ Include PR Review route
app.include_router(pr_review.router)

# 👉 Run command:
# uvicorn main:app --reload --host 0.0.0.0
