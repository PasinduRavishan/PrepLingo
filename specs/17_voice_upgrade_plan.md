# SPEC 17 — Voice Interview Upgrade Plan

Status: Research & Planning
Date: 2026-03-25
Goal: Replace text-based interview flow with real-time voice conversation between the AI interviewer and the candidate

---

## Current Architecture (Text-Based)

```
User types answer (string)
        |
        v
POST /api/session/{id}/message  { content: "user's text answer" }
        |
        v
session_service.process_message()
   |-- EvaluationChain (scores the answer)     } asyncio.gather
   |-- QuestionChain  (generates next question) }
        |
        v
JSON response: { ai_question, evaluation, question_number, session_complete }
        |
        v
Streamlit renders text on screen
```

The LLM pipeline (Groq) operates entirely on text. Voice is an I/O layer change — the core LangChain pipeline stays untouched.

---

## Voice Architecture (Proposed)

```
User speaks into mic (browser)
        |
        v  [STT: speech -> text]
Transcribed text (string)
        |
        v
POST /api/session/{id}/message  { content: "transcribed text" }   <-- same API
        |
        v
session_service.process_message()   <-- unchanged
        |
        v
JSON response: { ai_question: "text string", ... }
        |
        v  [TTS: text -> audio]
Audio plays back to user (browser)
```

**Key insight:** Voice plugs in at two edges only:
1. **Input edge** — User speech -> STT -> text string -> existing API
2. **Output edge** — AI question text -> TTS -> audio playback

The backend LangChain pipeline, Groq LLM, ChromaDB retrieval, and evaluation logic require zero changes.

---

## Technology Options

### Speech-to-Text (STT)

| Option | Type | Latency | Accuracy | Cost | Notes |
|--------|------|---------|----------|------|-------|
| **Web Speech API** | Browser-native | ~300ms | Good (Chrome) | Free | Chrome/Edge only. Sends audio to Google servers. No Firefox/Safari support for recognition. |
| **OpenAI Whisper API** | Cloud API | ~1-3s | Excellent | $0.006/min | Best accuracy/price ratio. Simple REST call. |
| **OpenAI GPT-4o Mini Transcribe** | Cloud API | ~1-2s | Excellent | $0.003/min | 50% cheaper than Whisper, newer model. |
| **Deepgram** | Cloud API | ~300ms | Very good | $0.0043-0.0092/min | Fastest cloud STT. Streaming support. |
| **Whisper (self-hosted)** | Local | ~2-5s | Excellent | Free | Requires GPU. Too heavy for e2-medium VM. |
| **Google Cloud STT** | Cloud API | ~500ms | Very good | $0.024/min | 60 min/month free. Expensive at scale. |

### Text-to-Speech (TTS)

| Option | Type | Latency | Voice Quality | Cost | Notes |
|--------|------|---------|---------------|------|-------|
| **Browser SpeechSynthesis** | Browser-native | Instant | Robotic | Free | Works offline. All browsers. Sounds artificial. |
| **ElevenLabs** | Cloud API | ~500ms | Human-like | Free: 10k chars/mo, Starter: $5/mo (30k chars) | Best voice quality. Streaming support. |
| **OpenAI TTS** | Cloud API | ~500ms | Very natural | $15/1M chars (~$0.015/1k chars) | Good quality, simple API. |
| **Google Cloud TTS** | Cloud API | ~300ms | Good-Natural | $4-16/1M chars | WaveNet/Neural2 voices sound good. |
| **Deepgram Aura** | Cloud API | ~250ms | Good | $0.0065/1k chars | Fast, affordable TTS. |
| **Coqui/XTTS (self-hosted)** | Local | ~1-3s | Good | Free | Requires GPU. Not viable on e2-medium. |

### Real-Time Voice Frameworks

| Framework | What It Does | Self-Hosted? | Cost |
|-----------|-------------|-------------|------|
| **Pipecat** | Python framework: STT -> LLM -> TTS pipeline with transport layer | Yes (open source) | Free (you pay for STT/TTS APIs) |
| **LiveKit** | WebRTC server + agents SDK for real-time voice AI | Yes (open source) | Free self-hosted, or LiveKit Cloud |
| **OpenAI Realtime API** | End-to-end voice-to-voice via GPT-4o | No (cloud only) | ~$0.04-0.30/min |
| **Daily.co** | WebRTC transport (pairs with Pipecat) | Cloud only | Free tier: 2k mins/mo |

---

## Architecture Options

### Option A — Browser-Native (Simplest, Free)

```
Browser: SpeechRecognition API  -->  text  -->  existing API
Browser: SpeechSynthesis API    <--  text  <--  existing API
```

**Pros:** Zero backend changes. Zero cost. No new dependencies.
**Cons:** Chrome/Edge only. Robotic TTS voice. Recognition requires internet (sends to Google). No Firefox/Safari STT support. Unreliable — SpeechRecognition and SpeechSynthesis conflict when used together.

**Verdict:** Good for a quick prototype, not production quality.

---

### Option B — Cloud STT + Cloud TTS via Frontend (Recommended for V1)

```
Browser mic  -->  audio blob  -->  Streamlit sends to backend
Backend:  /api/voice/transcribe   -->  Whisper API  -->  text
Backend:  process_message(text)   -->  ai_question text
Backend:  /api/voice/synthesize   -->  ElevenLabs/OpenAI TTS  -->  audio
Browser:  plays audio response
```

**New backend endpoints:**
- `POST /api/voice/transcribe` — accepts audio file, returns transcribed text
- `POST /api/voice/synthesize` — accepts text, returns audio file (or streaming audio)
- `POST /api/session/{id}/voice-message` — combined: accepts audio, returns audio + evaluation JSON

**Pros:** Works on all browsers. High-quality voices. Leverages existing pipeline. Moderate complexity.
**Cons:** Round-trip latency (~2-4s total). Not truly real-time conversational. Requires API keys and has per-use cost.

**Estimated cost per interview (10 questions, ~15 min):**
- STT (Whisper): 15 min x $0.006 = $0.09
- TTS (ElevenLabs Starter or OpenAI): ~5k chars x $0.015/1k = $0.075
- **Total: ~$0.17/interview** (on top of existing Groq free tier)

---

### Option C — Pipecat Real-Time Pipeline (Best Experience)

```
Browser  <-- WebRTC (Daily.co transport) -->  Pipecat Server
                                                |
                                          STT (Deepgram streaming)
                                                |
                                          LLM (Groq via LangChain)
                                                |
                                          TTS (ElevenLabs streaming)
                                                |
                                          Audio stream back to browser
```

**Pros:** Sub-second latency (~500-800ms). Natural conversation feel with interruption handling. Turn detection built in. Production-grade voice AI.
**Cons:** Significant architecture change. Requires Pipecat server alongside existing backend. Needs WebRTC transport (Daily.co or LiveKit). More complex deployment.

**Estimated cost per interview:**
- STT (Deepgram): 15 min x $0.005 = $0.075
- TTS (ElevenLabs): ~5k chars ~ $0.075
- Transport (Daily.co free tier): 2,000 min/mo free
- **Total: ~$0.15/interview**

---

### Option D — OpenAI Realtime API (Highest Quality, Highest Cost)

```
Browser  <-- WebSocket -->  OpenAI Realtime API (gpt-4o-realtime)
```

**Pros:** Lowest latency. Single API handles STT + LLM + TTS. Best conversation quality.
**Cons:** Replaces Groq entirely (no free tier). Very expensive (~$0.30/min = $4.50/interview). Vendor lock-in. Cannot use existing LangChain chains or RAG pipeline without significant rework.

**Verdict:** Too expensive and incompatible with current architecture. Not recommended.

---

## Recommendation

### Phase 1 — Option B (Cloud STT + TTS, ~1-2 weeks)

Start with Option B. It requires minimal backend changes (2-3 new endpoints), keeps the entire existing pipeline intact, and delivers a working voice interview at ~$0.17/interview.

**Implementation plan:**

1. **Backend: Add voice endpoints**
   - `POST /api/voice/transcribe` — receives audio (WebM/WAV), calls Whisper API, returns `{ text: "..." }`
   - `POST /api/voice/synthesize` — receives `{ text: "..." }`, calls OpenAI TTS or ElevenLabs, returns audio bytes
   - `POST /api/session/{id}/voice-message` — combined endpoint: audio in -> transcribe -> process_message -> synthesize -> audio out + JSON evaluation

2. **Backend: Add STT/TTS service layer**
   - `backend/app/services/voice_service.py` — wraps Whisper + TTS API calls
   - Add `OPENAI_API_KEY` (for Whisper + TTS) or `ELEVENLABS_API_KEY` to config

3. **Frontend: Voice recording UI**
   - Add mic record button (MediaRecorder API — works all browsers)
   - Record user's answer as audio blob
   - Send to `/api/session/{id}/voice-message`
   - Receive audio response, play via `<audio>` element
   - Keep text display as fallback/transcript

4. **Frontend: Mode toggle**
   - "Text Mode" / "Voice Mode" toggle in session setup
   - Voice mode shows mic button instead of text input
   - Evaluation scores still displayed as text cards

**Key files to modify:**
- `backend/app/api/routes/session.py` — new voice endpoint
- `backend/app/services/voice_service.py` — new file
- `backend/app/config.py` — new API key configs
- `frontend_streamlit/app.py` — voice UI components

### Phase 2 — Option C (Pipecat, if demand warrants)

If Phase 1 proves the concept and users want faster, more natural conversation, upgrade to Pipecat with streaming STT/TTS. This is a larger effort (~3-4 weeks) but delivers sub-second latency.

---

## Cost Summary

| Approach | Cost/Interview | Monthly (50 interviews) | Setup Complexity |
|----------|---------------|------------------------|-----------------|
| Text only (current) | $0.00 (Groq free) | $0.00 | Done |
| **Option B (Recommended)** | ~$0.17 | ~$8.50 | Low |
| Option C (Pipecat) | ~$0.15 | ~$7.50 | High |
| Option D (OpenAI Realtime) | ~$4.50 | ~$225 | Medium |

---

## Technical Feasibility on Current Infrastructure

| Concern | Assessment |
|---------|-----------|
| GCP e2-medium (4 GB RAM) | Sufficient — STT/TTS are cloud API calls, no local model needed |
| Docker Compose | Add no new containers — voice service lives inside existing backend |
| Streamlit | MediaRecorder API works in Streamlit via `st.audio_input()` (Streamlit 1.33+) or custom HTML component |
| Groq free tier | Unaffected — voice is I/O layer only, same number of LLM calls |
| Latency budget | STT (~1-2s) + LLM (~1-2s) + TTS (~0.5-1s) = ~3-5s total round-trip. Acceptable for interview format. |

---

## API Keys Required (Phase 1)

| Service | Key | Free Tier | Paid |
|---------|-----|-----------|------|
| **OpenAI** (Whisper + TTS) | `OPENAI_API_KEY` | $5 free credit on signup | Pay-as-you-go |
| **ElevenLabs** (TTS alternative) | `ELEVENLABS_API_KEY` | 10k chars/mo (~10 min) | $5/mo Starter |

One OpenAI API key covers both STT (Whisper) and TTS — simplest setup.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| STT misrecognizes technical terms | Show transcript for user to verify/edit before submission |
| TTS sounds unnatural | ElevenLabs or OpenAI TTS both sound very natural; avoid browser SpeechSynthesis |
| Latency too high (>5s) | Use streaming TTS (play audio as it generates). Deepgram streaming STT for faster recognition. |
| Cost growth | Track usage. Set per-user daily limits. Fall back to text mode if quota exceeded. |
| Streamlit audio limitations | Use `st.audio_input()` for recording, `st.audio()` for playback. If insufficient, use custom HTML component with MediaRecorder. |

---

## Decision Required

**Recommended next step:** Approve Option B (Cloud STT + TTS) as Phase 1 target. The primary decision is which TTS provider:

1. **OpenAI TTS** — One API key for both STT and TTS. Good voice quality. Simpler setup.
2. **ElevenLabs** — Best voice quality. Separate API key. Free tier for testing.

Both work. OpenAI is simpler (one key, one vendor). ElevenLabs sounds slightly better.
