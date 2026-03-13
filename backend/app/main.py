"""
main.py — FastAPI Application Entry Point

CONCEPTS EXPLAINED:

  LIFESPAN (contextlib.asynccontextmanager):
    Modern FastAPI uses "lifespan" events instead of @app.on_event("startup").
    - Code BEFORE yield: runs when app starts (create DB tables, load models)
    - Code AFTER yield:  runs when app shuts down (cleanup)
    
  CORS MIDDLEWARE:
    Browsers enforce the "Same-Origin Policy" — they block JavaScript from
    making API calls to a DIFFERENT origin (different port = different origin).
    
    Our setup:
      Frontend: http://localhost:3000
      Backend:  http://localhost:8000  ← different port = CORS issue!
    
    CORSMiddleware tells the browser: "localhost:3000 is allowed to call me".
    Without this, every API call from Next.js would be blocked in the browser.

  ROUTERS:
    Instead of putting all endpoints in main.py, we split them into separate
    files (routes/auth.py, routes/session.py, etc.). Each file is a Router.
    
    app.include_router(...) registers all routes from that file,
    with a prefix so all routes in session.py start with /api/session.
    
  AUTO-GENERATED DOCS:
    FastAPI automatically generates Swagger UI at /docs
    Visit http://localhost:8000/docs to see and test all endpoints!
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import create_tables
from app.api.routes import auth, resume, session, report


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    # ── STARTUP ──────────────────────────────────────────────
    print("🚀 PrepLingo API starting...")
    create_tables()
    print("✅ Database tables ready")
    print("📖 API docs available at: http://localhost:8000/docs")

    yield  # App is running

    # ── SHUTDOWN ─────────────────────────────────────────────
    print("👋 PrepLingo API shutting down")


app = FastAPI(
    title="PrepLingo API",
    description="AI Interview Trainer — powered by LangChain + Gemini + RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS Configuration ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route Registration ────────────────────────────────────────────
# Each router adds its endpoints with the given prefix
app.include_router(auth.router,    prefix="/api/auth",    tags=["🔐 Auth"])
app.include_router(resume.router,  prefix="/api/resume",  tags=["📄 Resume"])
app.include_router(session.router, prefix="/api/session", tags=["💬 Session"])
app.include_router(report.router,  prefix="/api/report",  tags=["📊 Report"])


# ── Health Check ──────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """
    Simple health check endpoint.
    Test with: curl http://localhost:8000/health
    Should return: {"status": "ok"}
    """
    return {"status": "ok", "app": "PrepLingo", "version": "0.1.0"}
