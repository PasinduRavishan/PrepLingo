"""
routes/auth.py — Authentication Endpoints

PHASE: Deferred (Guest Mode active for now)

WHAT THIS WILL HAVE (Phase 5+):
  POST /api/auth/register  — Create new account
  POST /api/auth/login     — Get JWT token
  POST /api/auth/refresh   — Refresh expired token

GUEST MODE EXPLANATION:
  Right now, the frontend generates a UUID in the browser:
    const guestId = localStorage.getItem('guest_id') 
                    || crypto.randomUUID();
    localStorage.setItem('guest_id', guestId);

  This guestId is sent with every API request as a query param or header.
  The backend uses it to associate resumes + sessions to "a person"
  without requiring a login.

  This is common in B2C apps — let users try the product before signing up.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def auth_status():
    """
    Current auth mode indicator.
    Frontend can call this to know if auth is required.
    """
    return {
        "mode": "guest",
        "message": "Guest mode active. No login required.",
        "note": "Full JWT auth coming in Phase 5"
    }
