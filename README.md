# 🌍 Language Translation Tool

FastAPI backend + Streamlit frontend for translating text across many languages. It uses a multi-provider strategy for reliability:

- Hugging Face Inference API (if `HUGGINGFACE_API_KEY` is set)
- LibreTranslate public instances (fallback)
- MyMemory free translator with chunking for long texts (final fallback)

Extras:
- Text-to-speech (gTTS) for translated output
- Download translated text and audio
- Dynamic language list from the backend

---

## Requirements
- Python 3.10+
- Windows (tested), but cross-platform should also work
- Optional: Hugging Face API key for best results

## Setup
1. Open a terminal in the project root.
2. Create and activate a virtual environment (Windows):
	- `python -m venv .venv`
	- `.venv\Scripts\activate`
3. Install dependencies:
	- `pip install -r backend/requirements.txt`
	- `pip install -r frontend/requirements.txt`

## Configure Environment
Create a file named `.env` in the project root with your Hugging Face API key. This file is git-ignored.

```
HUGGINGFACE_API_KEY=hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Optional: override default model
HUGGINGFACE_MODEL=facebook/m2m100_418M
```

Notes:
- HF translation is used first when `HUGGINGFACE_API_KEY` is present and `source_lang` is not `auto`.
- If HF is unavailable or errors, the backend falls back to LibreTranslate and then MyMemory.

## Run
In two terminals (with venv active):

1) Backend (FastAPI + Uvicorn)
- `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`
- API will be available at `http://127.0.0.1:8000`

2) Frontend (Streamlit)
- `python -m streamlit run frontend/app.py --server.port 8501`
- Open the URL shown in the terminal (typically `http://localhost:8501`)

## Streamlit Cloud (no backend)
You can deploy the Streamlit app alone. In this mode, it talks directly to translation providers.

1. In Streamlit Cloud, set Secrets:
	- `HUGGINGFACE_API_KEY = hf_...` (recommended)
	- Optional: `HUGGINGFACE_MODEL = facebook/m2m100_418M`
	- Optional: `BACKEND_URL = https://your-fastapi-host` (only if you deploy the backend)

2. Ensure frontend requirements include `deep-translator` (already added).

3. Deploy the app. The language dropdown will show the full list even without the backend. Translations will use HF → LibreTranslate → MyMemory fallbacks.

Notes:
- If `BACKEND_URL` is not set or unreachable, the app automatically uses providers directly.
- Avoid `Auto Detect` for very long texts for better reliability.

## Usage
- Enter text, choose source/target languages, click "Translate".
- For very long texts, avoid "Auto Detect" and specify the source language for better reliability.
- If speech is supported for the target language, you can play and download audio.
- Download the translated text using the download button.

## API
- `GET /` → health: `{ "status": "ok" }`
- `GET /languages` → returns `{ "languages": [{ "code": "en", "name": "English" }, ...] }`
- `POST /translate` → body `{ text, source_lang, target_lang }`, returns `{ "translated_text": "..." }`

See implementation in [backend/main.py](backend/main.py) and UI in [frontend/app.py](frontend/app.py).

## Troubleshooting
- 500/502 errors: Try selecting a specific source language; long texts may hit limits on free providers.
- "Could not reach the backend": Ensure the backend is running on `127.0.0.1:8000` and firewall allows local connections.
- Hugging Face not used: Verify `.env` is present, API key is valid, and source language is not `auto`.
- Port conflicts: Change `--server.port` for Streamlit or `--port` for Uvicorn.
- Virtual environment: Confirm the terminal shows `(venv)` and `python` resolves to `.venv\Scripts\python.exe`.

## Security
- `.env` is ignored by git to keep secrets out of the repository.

## Quick Test
Try translating "Hello world" from English to French. Expected result: "Bonjour le monde".

---

Happy translating!

