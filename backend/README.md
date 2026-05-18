# CoachModule Backend

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Start the API server:
   `uvicorn app.main:app --reload --port 8000`

## Configuration

- `CORS_ORIGINS` (optional): Comma-separated list of allowed frontend origins.
  Example: `http://localhost:3000,http://127.0.0.1:3000`
- `GEMINI_API_KEY` (required): Gemini API key for Live API WebSocket access.
- `GEMINI_LIVE_MODEL` (optional): Live API model name. Default: `gemini-3.1-flash-live-preview`.
- `GEMINI_LIVE_VOICE` (optional): Voice name for audio output. Default: `Kore`.
- `GEMINI_EVAL_MODEL` (optional): Model for evaluation reports. Default: `gemini-3-flash-preview`.
