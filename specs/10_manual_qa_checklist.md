# SPEC 10 - Manual QA Checklist (Swagger + Frontend Replay)

**Status:** Active  
**Date:** 2026-03-16  
**Scope:** Guest-mode MVP (no authentication)

---

## Purpose

Provide a repeatable manual QA checklist that verifies:
1. Swagger API flow correctness
2. Frontend replay flow correctness
3. Resume-aware interview behavior
4. Deterministic API error payload shape

---

## Preconditions

1. Backend server is running.
2. Frontend app is running.
3. Swagger is reachable at `/docs`.
4. A valid PDF resume is available.
5. Browser local storage has a `guest_id` (UUID-like string).

---

## Canonical Error Payload Contract

All known route errors in guest-mode flow should return:

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

Validation checks must confirm this shape for negative tests in resume/session/report flows.

---

## A. Swagger Flow Checklist

### A1. Upload Resume (Positive)

1. Open `POST /api/resume/upload`.
2. Set query `guest_id` to test guest value.
3. Attach a PDF file.
4. Execute.

Expected:
1. HTTP 200.
2. Response includes `resume_id`.
3. Response includes parsed resume fields (`parsed_skills`, `parsed_projects`).

### A2. Create Resume Session (Positive)

1. Open `POST /api/session/`.
2. Use body:
   - `guest_id`: same value as upload
   - `interview_type`: `resume`
   - `resume_id`: from step A1
3. Execute.

Expected:
1. HTTP 200.
2. Response includes `session_id` and `status`.

### A3. Start Session

1. Open `GET /api/session/{session_id}/start`.
2. Execute with created `session_id`.

Expected:
1. HTTP 200.
2. Response includes `ai_question`.
3. Question should reference uploaded resume context (project/skill cues).

### A4. Continue Session Loop

1. Call `POST /api/session/{session_id}/message` with answer text.
2. Repeat 2 to 3 turns.

Expected:
1. HTTP 200 per turn.
2. Response includes `evaluation` and next `ai_question`.
3. `question_number` increments correctly.

### A5. End and Report

1. Use `POST /api/session/{session_id}/end` or complete max questions.
2. Call `GET /api/report/{session_id}`.

Expected:
1. Session end returns completed status.
2. Report endpoint returns valid report object.
3. Arrays and scoring fields are non-malformed.

---

## B. Negative API Checks (Swagger)

### B1. Resume Session Without `resume_id`

1. `POST /api/session/` with `interview_type=resume` and `resume_id=null`.

Expected:
1. HTTP 400.
2. Error payload matches canonical shape.
3. `detail.error.code` is stable and descriptive.

### B2. Empty Answer Submission

1. `POST /api/session/{session_id}/message` with empty content.

Expected:
1. HTTP 400.
2. Error payload matches canonical shape.

### B3. Report Before Session Completion

1. Start a session but do not finish it.
2. Call `GET /api/report/{session_id}`.

Expected:
1. HTTP 400 (or expected policy status).
2. Error payload matches canonical shape.

---

## C. Frontend Replay Checklist

### C1. Fresh Guest User Replay

1. Clear site storage.
2. Open app and confirm guest mode initializes.
3. Upload a resume from UI.
4. Start resume interview from UI.
5. Complete at least 2 turns.
6. End session and open report page.

Expected:
1. No blocking auth prompts.
2. Session starts and progresses normally.
3. Questions are resume-aware.
4. Report page renders with valid data.

### C2. Existing Guest Replay

1. Keep existing local storage.
2. Refresh dashboard.
3. Verify latest resume/session continuity behavior.

Expected:
1. Existing guest context is reused.
2. Latest resume can be selected/used for interview.
3. No guest data crossover across IDs.

---

## Pass Criteria

Checklist is considered pass when:
1. All positive flows succeed.
2. Required negative checks return deterministic structured errors.
3. Frontend replay shows stable guest-mode UX and report flow.
