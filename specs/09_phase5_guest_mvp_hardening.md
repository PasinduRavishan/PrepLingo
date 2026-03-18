# SPEC 09 — Phase 5 Implementation Plan: Guest-Mode MVP Hardening

**Status:** 🟢 IN PROGRESS (Hardening block implemented)  
**Date:** 2026-03-16  
**Goal:** Ship a stable, high-quality guest-mode MVP before introducing auth.

**Implemented in this block:**
1. Session creation validation for resume-mode (`resume_id` required + ownership check)
2. Flow guard: disallow sending answers before session start
3. Guest resume lookup returns latest resume deterministically
4. Relevance check script added: `backend/scripts/test_phase5_pdf_relevance.py`
5. Edge-case suite added: `backend/scripts/test_phase5_edge_cases.py`
6. Unified API error response shape in `resume.py`, `session.py`, and `report.py`
7. Multi-format RAG knowledge ingestion (`.md`, `.txt`, `.pdf`, `.docx`, `.html`)

---

## Why This Phase

The core platform flow is already implemented:
1. Resume ingestion (Phase 2)
2. Interview session + evaluation loop (Phase 3)
3. Final report generation (Phase 4)

To hit MVP quality, the highest leverage next step is hardening reliability, UX behavior, and evaluation quality in guest mode.

---

## Final Goal (Current Product Strategy)

Any user should be able to:
1. Open app
2. Upload resume PDF
3. Start interview
4. Complete interview
5. Receive useful report

All without login/signup.

---

## Scope of Phase 5

### In Scope

1. Reliability hardening for guest-mode flows
2. Better error handling and API responses
3. Resume and session edge-case coverage
4. Report quality and consistency checks
5. End-to-end test checklist and automation updates
6. Docs/spec alignment with guest-mode strategy

### Out of Scope

1. JWT auth/login/register
2. Multi-user account management
3. Payment/subscription systems
4. Production infra redesign

---

## Workstreams and Tasks

### Workstream A — API/Backend Hardening

1. Standardize error responses in routes:
   - `resume.py`, `session.py`, `report.py`
2. Enforce consistent validation messages:
   - empty answer
   - invalid session state
   - missing/invalid resume inputs
3. Add explicit status handling for interrupted/partial sessions.
4. Ensure report endpoint handles all expected session states cleanly.

**Acceptance Criteria:**
- No unhandled exceptions for common bad inputs.
- Errors are user-readable and deterministic.
- Errors follow one canonical payload shape:

```json
{
   "detail": {
      "error": {
         "code": "STRING_ERROR_CODE",
         "message": "Human-readable message",
         "context": {}
      }
   }
}
```

**Current Coverage:**
- ✅ Missing `resume_id` for resume interview returns 400
- ✅ Resume ownership mismatch returns 403
- ✅ Message-before-start returns 400
- ✅ Report-before-completion returns 400
- ✅ Shared structured error payload is used across Phase 2/3/4 route surface for guest-mode flows

---

### Workstream B — Flow Integrity

1. Verify upload -> interview -> report sequence under normal and partial paths.
2. Verify manual end behavior produces expected report behavior.
3. Verify regenerate report behavior stays idempotent and safe.
4. Verify session/history retrieval consistency for in-progress and completed sessions.

**Acceptance Criteria:**
- End-to-end guest flow passes manually and via scripts.
- No data corruption across repeated retries.

---

### Workstream C — Evaluation and Report Quality

1. Calibrate prompts where low-quality generic feedback appears.
2. Ensure report fields are never malformed:
   - per-question scores
   - per-dimension scores
   - strengths/weaknesses/suggestions arrays
3. Add guardrails for low-information answers.

**Acceptance Criteria:**
- Reports are structurally valid for all tested sessions.
- Feedback quality is acceptable across all interview types.

---

### Workstream D — Test and QA Expansion

1. Keep existing phase tests green:
   - `test_phase2_resume.py`
   - `test_phase3_session.py`
   - `test_phase4_report.py`
2. Add/extend tests for edge cases:
   - invalid file upload
   - empty message
   - report before completion
   - session resume/reload behavior
3. Define a final manual QA checklist in docs.
4. Keep a testing flow guide spec with replay steps for Swagger and frontend.
5. Keep RAG ingestion docs updated for new knowledge source types.

**Acceptance Criteria:**
- Test scripts pass reliably in documented environment.
- Manual QA checklist can be executed by another developer.

**Current Test Scripts:**
1. `backend/scripts/test_phase5_pdf_relevance.py`
2. `backend/scripts/test_phase5_edge_cases.py`
3. `specs/10_manual_qa_checklist.md` (manual execution checklist)
4. `specs/11_testing_flow_guide.md` (testing-flow guide spec)

---

## Proposed Execution Order

1. Backend/API hardening
2. Flow integrity checks
3. Evaluation/report quality tuning
4. Test expansions and regression run
5. Docs/spec finalization

---

## Definition of Done (Phase 5)

Phase 5 is complete when:

1. Guest-mode MVP flow works reliably end-to-end.
2. Known edge cases have explicit handling and tested outcomes.
3. Phase 2/3/4 tests remain green and Phase 5 checks pass.
4. Specs and project docs reflect the current guest-mode strategy.
5. Team can defer auth confidently without blocking user trials.

---

## How To Validate Resume Relevance (PDF Test)

Yes, this can be tested directly with a real PDF upload.

### Manual Swagger Flow

1. `POST /api/resume/upload?guest_id=<your_uuid>` with PDF
2. `POST /api/session/` with:
   - `interview_type = "resume"`
   - `resume_id` returned from upload
3. `GET /api/session/{session_id}/start`
4. Check the AI question mentions project/skill details from uploaded resume.

### Automated Check Script

Use:

`backend/scripts/test_phase5_pdf_relevance.py`

It validates:
1. Resume upload works
2. Resume interview creation requires `resume_id`
3. First question is checked against distinctive resume keywords (heuristic grounding check)

---

## Test Evidence (Executed)

### Edge-case Suite

`backend/scripts/test_phase5_edge_cases.py` passed with:

1. ✅ Missing `resume_id` for resume mode blocked (400)
2. ✅ Resume ownership mismatch blocked (403)
3. ✅ Message before `/start` blocked (400)
4. ✅ Report before completion blocked (400)
5. ✅ Latest resume-by-guest returns newest record

### PDF Relevance Suite

`backend/scripts/test_phase5_pdf_relevance.py` passed with:

1. ✅ PDF upload succeeded and resume parsed
2. ✅ Resume session created with uploaded `resume_id`
3. ✅ First AI question referenced uploaded project context (`PrepLingo`)
4. ✅ Resume-mode validation without `resume_id` blocked (400)

---

## After Phase 5

When guest MVP is stable, Phase 6 can introduce auth safely:
1. Register/login/refresh
2. Account-linked data ownership
3. Optional guest-to-account migration
