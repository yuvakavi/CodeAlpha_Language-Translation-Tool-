import streamlit as st
import requests
import io
import json
from gtts import gTTS
from gtts.lang import tts_langs

st.set_page_config(page_title="🌍 Language Translator", page_icon="🌍", layout="centered")

# Subtle UI polish
st.markdown(
    """
    <style>
    .stButton>button {background:#4A90E2;color:white;border-radius:8px;padding:0.6rem 1rem;font-weight:600;border:0}
    .stDownloadButton>button {border-radius:8px}
    .lang-select label {font-weight:600}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌍 Language Translation Tool")
st.caption("Translate text across many languages. Supports speech and download.")

text = st.text_area("✍️ Enter text", placeholder="Type or paste your text here...")
st.caption(f"Characters: {len(text)}")

API_BASE = "http://127.0.0.1:8000"

# Load full language list from backend
def load_languages():
    try:
        r = requests.get(f"{API_BASE}/languages", timeout=10)
        if r.ok:
            data = r.json().get("languages", [])
            # Return dict name->code for display
            return {item["name"]: item["code"] for item in data}
    except requests.RequestException:
        pass
    # Fallback minimal list if backend unreachable
    return {
        "English": "en",
        "Tamil": "ta",
        "Hindi": "hi",
        "French": "fr",
        "Spanish": "es",
        "German": "de",
    }

# Allow Auto Detect only for source, not target
base_languages = load_languages()
source_languages = {"Auto Detect": "auto", **base_languages}
target_languages = base_languages

source_options = sorted(source_languages.keys())
target_options = sorted(target_languages.keys())

# Default to English if present
default_source = source_options.index("English") if "English" in source_options else 0
default_target = target_options.index("English") if "English" in target_options else 0

col1, col2 = st.columns(2)
with col1:
    source_name = st.selectbox("Source Language", source_options, index=default_source)
with col2:
    target_name = st.selectbox("Target Language", target_options, index=default_target)

st.divider()
if st.button("🚀 Translate"):
    if not text.strip():
        st.warning("Please enter some text to translate.")
    else:
        if len(text) > 500 and source_name == "Auto Detect":
            st.info("For long texts, select a specific Source Language to improve reliability.")
        payload = {
            "text": text,
            "source_lang": source_languages[source_name],
            "target_lang": target_languages[target_name]
        }

        API_URL = f"{API_BASE}/translate"

        with st.spinner("Translating..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=30)
            except requests.RequestException as e:
                st.error(f"Could not reach the backend: {e}")
            else:
                if response.ok:
                    data = response.json()
                    translated = data.get("translated_text", "")
                    if translated:
                        st.success("✅ Translated Text")
                        st.code(translated)

                                                # Copy button removed per request

                        # Download translated text
                        st.download_button(
                            "⬇️ Download Text",
                            translated,
                            file_name="translation.txt",
                        )

                        # Text-to-speech for the translated output (target language only)
                        supported_tts = tts_langs()
                        # Map certain codes to gTTS equivalents
                        tts_code_map = {
                            "zh": "zh-CN",  # default to Simplified Chinese
                            "tl": "fil",    # gTTS uses 'fil' for Filipino
                            "no": "no",     # Norwegian (Bokmål)
                        }
                        tts_lang = tts_code_map.get(target_languages[target_name], target_languages[target_name])
                        if tts_lang in supported_tts:
                            try:
                                tts = gTTS(text=translated, lang=tts_lang)
                                audio_buf = io.BytesIO()
                                tts.write_to_fp(audio_buf)
                                audio_buf.seek(0)
                                st.audio(audio_buf, format="audio/mp3")
                                st.download_button(
                                    "🔊 Download Audio",
                                    audio_buf.getvalue(),
                                    file_name="translation.mp3",
                                    mime="audio/mpeg",
                                )
                            except Exception as e:
                                st.info(f"Speech not available for {target_name}: {e}")
                        else:
                            st.info(f"Speech not supported for target language: {target_name}")
                    else:
                        st.error("Backend returned no translated text.")
                else:
                    # Show backend error details if provided
                    try:
                        err = response.json().get("detail")
                    except Exception:
                        err = response.text
                    st.error(f"Translation failed ({response.status_code}).\n{err}")
