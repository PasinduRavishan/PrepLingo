import os
import uuid
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests
import streamlit as st

# Reads BACKEND_URL env var injected by docker-compose.
# Falls back to localhost for direct local dev (no Docker).
_DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


@dataclass
class ApiResult:
    ok: bool
    status_code: int
    data: dict[str, Any] | None = None
    error: str | None = None


def parse_api_error(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except Exception:
        return f"HTTP {resp.status_code}: {resp.text[:240]}"

    detail = payload.get("detail")
    if isinstance(detail, dict):
        err = detail.get("error")
        if isinstance(err, dict):
            code = err.get("code", "UNKNOWN")
            message = err.get("message", "Request failed")
            return f"{code}: {message}"

    if isinstance(detail, str):
        return detail
    return f"HTTP {resp.status_code}: {payload}"


def api_call(
    method: str,
    base_url: str,
    path: str,
    *,
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: int = 90,
) -> ApiResult:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        resp = requests.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            files=files,
            timeout=timeout,
        )
    except requests.Timeout:
        return ApiResult(
            ok=False,
            status_code=0,
            error=f"Request timed out after {timeout} seconds",
        )
    except requests.RequestException as exc:
        return ApiResult(ok=False, status_code=0, error=str(exc))

    if 200 <= resp.status_code < 300:
        try:
            data = resp.json()
            return ApiResult(ok=True, status_code=resp.status_code, data=data)
        except Exception:
            return ApiResult(ok=True, status_code=resp.status_code, data={})

    return ApiResult(ok=False, status_code=resp.status_code, error=parse_api_error(resp))


def ensure_state() -> None:
    defaults = {
        "backend_url": _DEFAULT_BACKEND_URL,
        "guest_id": str(uuid.uuid4()),
        "resume_id": None,
        "resume_data": None,
        "session_id": None,
        "interview_type": "technical",
        "messages": [],
        "started": False,
        "session_complete": False,
        "last_evaluation": None,
        "last_report": None,
        "max_questions": 8,
        "resume_chunks_embedded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_flow() -> None:
    preserved = {
        "backend_url": st.session_state.backend_url,
        "guest_id": st.session_state.guest_id,
    }
    st.session_state.clear()
    for key, value in preserved.items():
        st.session_state[key] = value
    ensure_state()


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

          :root {
            --bg-warm: #f6f4ee;
            --ink: #111827;
            --ink-soft: #4b5563;
            --accent: #0f766e;
            --accent-soft: #d1fae5;
            --panel: #fffdf8;
            --line: #e7e3d5;
          }

          .stApp {
            background:
              radial-gradient(1000px 480px at 95% -8%, #b8f3e4 0%, transparent 55%),
              radial-gradient(760px 460px at -5% 20%, #fde2a7 0%, transparent 52%),
              var(--bg-warm);
          }

          h1, h2, h3 {
            font-family: 'Fraunces', Georgia, serif !important;
            color: var(--ink) !important;
            letter-spacing: -0.02em;
          }

          p, label, span, div, button {
            font-family: 'Space Grotesk', 'Avenir Next', 'Segoe UI', sans-serif !important;
          }

          .hero {
            padding: 1.2rem 1.2rem 1.3rem 1.2rem;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: linear-gradient(145deg, #ffffff 0%, #f8f7f1 100%);
            box-shadow: 0 12px 30px rgba(17, 24, 39, 0.07);
            margin-bottom: 1rem;
          }

          .chip {
            display: inline-block;
            padding: 0.28rem 0.7rem;
            margin-right: 0.4rem;
            border-radius: 999px;
            border: 1px solid #99f6e4;
            background: var(--accent-soft);
            color: #065f46;
            font-size: 0.82rem;
            font-weight: 600;
          }

          .step-card {
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 0.95rem;
            background: var(--panel);
          }

          .eval-card {
            border: 1px solid #c7f9d4;
            background: #f0fdf4;
            border-radius: 14px;
            padding: 0.8rem;
          }

          .report-card {
            border: 1px solid #bae6fd;
            background: #f0f9ff;
            border-radius: 16px;
            padding: 0.9rem;
          }

                    .turn-card {
                        border: 1px solid var(--line);
                        border-radius: 16px;
                        padding: 0.9rem;
                        background: #fffefb;
                        margin: 0.65rem 0;
                    }

                    .turn-head {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        margin-bottom: 0.45rem;
                    }

                    .turn-tag {
                        font-size: 0.77rem;
                        font-weight: 700;
                        padding: 0.2rem 0.5rem;
                        border-radius: 999px;
                        border: 1px solid #a7f3d0;
                        color: #065f46;
                        background: #ecfdf5;
                    }

                    .turn-q {
                        border-left: 3px solid #0f766e;
                        padding: 0.5rem 0.75rem;
                        background: #f0fdfa;
                        border-radius: 10px;
                    }

                    .turn-a {
                        border-left: 3px solid #2563eb;
                        padding: 0.5rem 0.75rem;
                        background: #eff6ff;
                        border-radius: 10px;
                        margin-top: 0.55rem;
                    }

                    .awaiting {
                        color: var(--ink-soft);
                        font-size: 0.88rem;
                        margin-top: 0.5rem;
                    }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1 style="margin:0;">PrepLingo Interview Studio</h1>
          <p style="margin:0.35rem 0 0.75rem 0;color:#374151;">
            Resume-grounded AI interviews with live scoring and instant final reports.
          </p>
          <span class="chip">Guest Mode</span>
          <span class="chip">RAG + Resume Context</span>
          <span class="chip">Session Evaluations</span>
        </div>
        """,
        unsafe_allow_html=True,
    )



def resume_step() -> None:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.subheader("1) Upload Resume")
    uploaded = st.file_uploader("Drop your PDF resume", type=["pdf"])

    if uploaded and st.button("Process Resume", type="primary"):
        with st.spinner("Extracting and parsing CV with AI..."):
            files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
            res = api_call(
                "POST",
                st.session_state.backend_url,
                "/api/resume/upload",
                params={"guest_id": st.session_state.guest_id},
                files=files,
                timeout=120,
            )

        if not res.ok:
            # Backend may finish after the client timeout — try to recover.
            error_text = (res.error or "").lower()
            if "timed out" in error_text:
                recover = api_call(
                    "GET",
                    st.session_state.backend_url,
                    f"/api/resume/guest/{st.session_state.guest_id}",
                    timeout=30,
                )
                recovered = recover.data if recover.ok else None
                if recovered:
                    st.session_state.resume_id = recovered.get("resume_id")
                    st.session_state.resume_data = {
                        "resume_id": recovered.get("resume_id"),
                        "parsed_skills": recovered.get("skills", []),
                        "parsed_projects": recovered.get("projects", []),
                    }
                    st.session_state.resume_chunks_embedded = bool(recovered.get("chunks_embedded", False))
                    st.warning("Upload timed out but resume was recovered.")
                else:
                    st.error("Upload timed out. Please try again.")
            else:
                st.error(res.error or "Resume upload failed")
        else:
            payload = res.data or {}
            st.session_state.resume_id = payload.get("resume_id")
            st.session_state.resume_data = payload
            st.session_state.resume_chunks_embedded = False
            st.success(
                f"CV parsed — found {len(payload.get('parsed_skills', []))} skills "
                f"and {len(payload.get('parsed_projects', []))} projects."
            )
            st.info("CV knowledge base building in background. Refresh below to check status.")

    if st.session_state.resume_id:
        st.caption(f"Resume ready: #{st.session_state.resume_id}")
        resume = st.session_state.resume_data or {}

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.resume_chunks_embedded:
                st.success("✅ CV knowledge base ready")
            else:
                st.info("⏳ CV knowledge base building...")
        with col2:
            if st.button("Refresh Status", use_container_width=True):
                check = api_call(
                    "GET",
                    st.session_state.backend_url,
                    f"/api/resume/{st.session_state.resume_id}/status",
                    timeout=10,
                )
                if check.ok and check.data:
                    st.session_state.resume_chunks_embedded = bool(check.data.get("chunks_embedded", False))
                    st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Skills Parsed", len(resume.get("parsed_skills", [])))
        with c2:
            st.metric("Projects Parsed", len(resume.get("parsed_projects", [])))

        top_skills = resume.get("parsed_skills", [])[:12]
        if top_skills:
            st.write("Top Skills")
            st.write(" • ".join(str(s) for s in top_skills))

    st.markdown("</div>", unsafe_allow_html=True)


def setup_session_step() -> None:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.subheader("2) Configure Interview")
    interview_type = st.selectbox(
        "Interview Type",
        options=["technical", "system_design", "behavioral", "resume"],
        index=["technical", "system_design", "behavioral", "resume"].index(
            st.session_state.interview_type
        ),
    )
    st.session_state.interview_type = interview_type

    missing_resume = interview_type == "resume" and not st.session_state.resume_id
    if missing_resume:
        st.warning("Resume interview needs a processed resume first.")

    resume_exists = bool(st.session_state.resume_id)
    cv_not_ready = resume_exists and not st.session_state.resume_chunks_embedded
    if cv_not_ready:
        st.info("CV knowledge base still building — interview will use parsed CV data for personalization until it's ready.")

    create_disabled = missing_resume  # Never block on embedding; interview works without vector chunks

    if st.button("Create Session", type="primary", disabled=create_disabled):
        payload = {
            "guest_id": st.session_state.guest_id,
            "interview_type": interview_type,
            "resume_id": st.session_state.resume_id if st.session_state.resume_id else None,
        }
        with st.spinner("Creating interview session..."):
            create_res = api_call(
                "POST",
                st.session_state.backend_url,
                "/api/session/",
                json_data=payload,
                timeout=60,
            )

        if not create_res.ok:
            st.error(create_res.error or "Could not create session")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        session_id = (create_res.data or {}).get("session_id")
        st.session_state.session_id = session_id
        st.session_state.max_questions = int((create_res.data or {}).get("max_questions", 8) or 8)

        with st.spinner("Generating first question..."):
            first_q = api_call(
                "GET",
                st.session_state.backend_url,
                f"/api/session/{session_id}/start",
                timeout=240,
            )

        if not first_q.ok:
            st.error(first_q.error or "Failed to start session")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        first_payload = first_q.data or {}
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": first_payload.get("ai_question", "Let's begin."),
                "question_number": first_payload.get("question_number", 1),
            }
        ]
        st.session_state.started = True
        st.session_state.session_complete = bool(first_payload.get("session_complete", False))
        st.success("Session is live")

    st.markdown("</div>", unsafe_allow_html=True)


def _build_turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    pending_answer_idx: dict[int, int] = {}

    for msg in messages:
        role = msg.get("role")

        if role == "assistant":
            qn = msg.get("question_number")
            if qn is None:
                continue

            turns.append(
                {
                    "question_number": qn,
                    "question": msg.get("content", ""),
                    "answer": None,
                    "evaluation": None,
                }
            )
            pending_answer_idx[qn] = len(turns) - 1
            continue

        if role == "user":
            answered_qn = msg.get("answered_question_number")
            if answered_qn is None:
                continue

            turn_idx = pending_answer_idx.get(answered_qn)
            if turn_idx is None:
                continue

            turns[turn_idx]["answer"] = msg.get("content", "")
            turns[turn_idx]["evaluation"] = msg.get("evaluation")

    return turns


def render_messages() -> None:
    st.caption("Interview Timeline")
    turns = _build_turns(st.session_state.messages)

    if not turns:
        st.info("Your first question will appear here.")
        return

    for turn in turns:
        qn = turn.get("question_number", "-")
        st.markdown('<div class="turn-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="turn-head"><strong>Question {qn}</strong><span class="turn-tag">Turn {qn}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="turn-q">', unsafe_allow_html=True)
        st.write(turn.get("question", ""))
        st.markdown("</div>", unsafe_allow_html=True)

        answer = turn.get("answer")
        if answer:
            st.markdown('<div class="turn-a">', unsafe_allow_html=True)
            st.caption("Your Answer")
            st.write(answer)
            st.markdown("</div>", unsafe_allow_html=True)

            evaluation = turn.get("evaluation")
            if evaluation and isinstance(evaluation, dict):
                st.markdown('<div class="eval-card">', unsafe_allow_html=True)
                cols = st.columns(4)
                cols[0].metric("Overall", evaluation.get("overall_score", "-"))
                cols[1].metric("Technical", evaluation.get("technical_correctness", "-"))
                cols[2].metric("Depth", evaluation.get("depth_of_explanation", "-"))
                cols[3].metric("Clarity", evaluation.get("clarity", "-"))

                strengths = evaluation.get("strengths", [])
                if strengths:
                    st.caption("Strengths")
                    for item in strengths[:3]:
                        st.write(f"- {item}")

                st.caption("Suggestions")
                for suggestion in evaluation.get("suggestions", [])[:3]:
                    st.write(f"- {suggestion}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="awaiting">Awaiting your answer...</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def interview_step() -> None:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.subheader("3) Interview Live")

    if not st.session_state.session_id or not st.session_state.started:
        st.info("Create and start a session to begin the interview chat.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    answered_count = sum(1 for msg in st.session_state.messages if msg.get("role") == "user")
    max_questions = max(int(st.session_state.max_questions or 8), 1)
    progress = min(answered_count / max_questions, 1.0)
    st.progress(progress, text=f"Progress: {answered_count}/{max_questions} answered")

    render_messages()

    if st.session_state.session_complete:
        st.success("Interview complete. Generate your report below.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    answer = st.chat_input("Write your answer and press Enter")
    if not answer:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    last_question_number = None
    for msg in reversed(st.session_state.messages):
        if msg.get("role") == "assistant":
            last_question_number = msg.get("question_number")
            break

    st.session_state.messages.append(
        {
            "role": "user",
            "content": answer,
            "answered_question_number": last_question_number,
        }
    )

    with st.spinner("Evaluating answer and generating next question..."):
        res = api_call(
            "POST",
            st.session_state.backend_url,
            f"/api/session/{st.session_state.session_id}/message",
            json_data={"content": answer},
            timeout=120,
        )

    if not res.ok:
        st.error(res.error or "Failed to process answer")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    payload = res.data or {}
    eval_payload = payload.get("evaluation")

    # Attach evaluation to the answer that was just submitted.
    for idx in range(len(st.session_state.messages) - 1, -1, -1):
        if st.session_state.messages[idx].get("role") == "user":
            st.session_state.messages[idx]["evaluation"] = eval_payload
            break

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": payload.get("ai_question", ""),
            "question_number": payload.get("question_number"),
        }
    )
    st.session_state.last_evaluation = eval_payload
    st.session_state.session_complete = bool(payload.get("session_complete", False))
    st.rerun()


def report_step() -> None:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("4) Final Report")

    if not st.session_state.session_id:
        st.info("No active session yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Fetch Report", type="primary", use_container_width=True):
            with st.spinner("Compiling report..."):
                res = api_call(
                    "GET",
                    st.session_state.backend_url,
                    f"/api/report/{st.session_state.session_id}",
                    timeout=90,
                )
            if res.ok:
                st.session_state.last_report = res.data
            else:
                st.error(res.error or "Report fetch failed")

    with col_b:
        if st.button("End Session Now", use_container_width=True):
            end_res = api_call(
                "POST",
                st.session_state.backend_url,
                f"/api/session/{st.session_state.session_id}/end",
                timeout=60,
            )
            if end_res.ok:
                st.session_state.session_complete = True
                st.success((end_res.data or {}).get("message", "Session ended"))
            else:
                st.error(end_res.error or "Could not end session")

    report = st.session_state.last_report
    if report:
        cols = st.columns(3)
        cols[0].metric("Overall Score", f"{report.get('overall_score', 0):.1f}")
        cols[1].metric("Questions", len(report.get("per_question_scores", [])))
        cols[2].metric("Interview Type", report.get("interview_type", "n/a"))

        q_scores = report.get("per_question_scores", [])
        if q_scores:
            chart_data = pd.DataFrame(
                {
                    "question": [f"Q{i+1}" for i in range(len(q_scores))],
                    "score": q_scores,
                }
            )
            st.bar_chart(chart_data.set_index("question"))

        strengths = report.get("top_strengths", [])
        weaknesses = report.get("top_weaknesses", [])
        suggestions = report.get("suggestions", [])

        left, right = st.columns(2)
        with left:
            st.caption("Top Strengths")
            for item in strengths[:5]:
                st.write(f"- {item}")

            st.caption("Top Weaknesses")
            for item in weaknesses[:5]:
                st.write(f"- {item}")

        with right:
            st.caption("Actionable Suggestions")
            for item in suggestions[:8]:
                st.write(f"- {item}")

    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="PrepLingo Interview Studio",
        page_icon="🧠",
        layout="wide",
    )

    ensure_state()
    inject_styles()
    render_header()

    top_left, top_right = st.columns([1.05, 1], gap="large")
    with top_left:
        resume_step()
    with top_right:
        setup_session_step()

    interview_step()
    report_step()


if __name__ == "__main__":
    main()
