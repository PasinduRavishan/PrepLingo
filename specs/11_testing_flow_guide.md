# SPEC 11 - Testing Flow Guide (Swagger + Script + Frontend Replay)

**Status:** Active  
**Date:** 2026-03-16  
**Goal:** One practical guide to replay and verify guest-mode end-to-end behavior.

---

## 1. Testing Layers

Use three layers in this order:

1. Script smoke checks
2. Swagger deterministic verification
3. Frontend replay validation

Frontend build and UX structure should follow [specs/12_frontend_architecture_and_ux_plan.md](specs/12_frontend_architecture_and_ux_plan.md) before execution of Layer 3 replay checks.

This order catches backend regressions quickly before UI-level debugging.

---

## 2. Layer 1: Script Smoke Checks

Run these checks first:

1. `backend/scripts/test_phase2_resume.py`
2. `backend/scripts/test_phase3_session.py`
3. `backend/scripts/test_phase4_report.py`
4. `backend/scripts/test_phase5_edge_cases.py`
5. `backend/scripts/test_phase5_pdf_relevance.py`

Expected:
1. All scripts pass.
2. No crash/traceback in backend logs for tested flows.

If a script fails:
1. Fix backend issue first.
2. Re-run only failed script.
3. Re-run full sequence before sign-off.

For RAG source updates, follow [specs/13_rag_knowledge_ingestion_and_content_plan.md](specs/13_rag_knowledge_ingestion_and_content_plan.md) before re-running smoke checks.

---

## 3. Layer 2: Swagger Deterministic Verification

Execute core flow manually:

1. Upload resume via `POST /api/resume/upload`.
2. Create session via `POST /api/session/`.
3. Start session via `GET /api/session/{id}/start`.
4. Iterate messages via `POST /api/session/{id}/message`.
5. End session via `POST /api/session/{id}/end` (or natural completion).
6. Fetch report via `GET /api/report/{id}`.

Verification focus:
1. Resume relevance in early questions.
2. Correct session transitions.
3. Stable report schema.
4. Canonical error payload shape on negative checks.

Negative checks required:
1. Missing `resume_id` for resume interview.
2. Empty answer submission.
3. Report fetch before completion.

---

## 4. Layer 3: Frontend Replay Validation

Replay full UX as a user:

1. Open app as guest.
2. Upload resume from UI.
3. Start resume interview.
4. Complete multiple answer turns.
5. End and open report screen.
6. Refresh and verify continuity behavior.

Validation focus:
1. No auth dependency in guest flow.
2. Resume-aware prompts still visible through UI.
3. No broken state after refresh/reopen.

---

## 5. Evidence Capture Template

For each test cycle, capture:

1. Date/time
2. Commit hash
3. Backend base URL
4. Script pass/fail summary
5. Swagger flow pass/fail summary
6. Frontend replay pass/fail summary
7. Notes on anomalies and mitigation

---

## 6. Release Gate (Guest MVP)

Guest MVP is releasable for trials when:

1. All script checks pass.
2. Swagger flow and required negative checks pass.
3. Frontend replay pass is confirmed.
4. Error responses are consistently structured.
5. No blocker bug remains open for upload -> session -> report journey.
