# PrepLingo Streamlit Frontend

Modern Streamlit UI for the complete PrepLingo guest-mode interview flow:

1. Upload resume (PDF)
2. Create and start interview session
3. Live Q&A with per-answer evaluation
4. Fetch final report with score visualization

## Run

From repo root:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend_streamlit
source ../.venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the Streamlit URL shown in terminal (typically http://localhost:8501).

## Notes

- Backend default expected URL is `http://127.0.0.1:8000`.
- Streamlit app works with guest mode (no login needed).
- For `resume` interview type, upload a resume first.
