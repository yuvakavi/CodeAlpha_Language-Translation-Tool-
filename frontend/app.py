import streamlit as st
import requests
import io
import os
from gtts import gTTS
from gtts.lang import tts_langs
from deep_translator import MyMemoryTranslator

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

def get_secret(name, default=None):
    # Prefer Streamlit secrets in cloud, else env variables
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)

# Optional backend URL (for when FastAPI is deployed). If not set, use direct providers.
API_BASE = get_secret("BACKEND_URL")

# Comprehensive language list fallback (when backend isn't reachable)
LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "as": "Assamese",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fil": "Filipino",
    "fr": "French",
    "gu": "Gujarati",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "ig": "Igbo",
    "it": "Italian",
    "ja": "Japanese",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ms": "Malay",
    "my": "Burmese",
    "nb": "Norwegian Bokmål",
    "ne": "Nepali",
    "nl": "Dutch",
    "no": "Norwegian",
    "or": "Odia",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tl": "Filipino",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "yo": "Yoruba",
    "zh": "Chinese",
    "zu": "Zulu",
    "xh": "Xhosa",
}

# Load full language list from backend
def load_languages():
    # Try backend first if configured
    if API_BASE:
        try:
            r = requests.get(f"{API_BASE}/languages", timeout=10)
            if r.ok:
                data = r.json().get("languages", [])
                return {item["name"]: item["code"] for item in data}
        except requests.RequestException:
            pass
    # Fallback to comprehensive local list
    return {LANGUAGE_NAMES[code]: code for code in sorted(LANGUAGE_NAMES.keys())}

# Cloud translation pipeline (HF → LibreTranslate → MyMemory)
def cloud_translate(text, source, target):
    errors = []

    # Hugging Face Inference API (if key exists and source not auto)
    HF_API_KEY = get_secret("HUGGINGFACE_API_KEY")
    HF_MODEL = get_secret("HUGGINGFACE_MODEL", "facebook/m2m100_418M")
    if HF_API_KEY and source != "auto":
        try:
            headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
            payload_hf = {"inputs": text, "parameters": {"src_lang": source, "tgt_lang": target}}
            r = requests.post(f"https://api-inference.huggingface.co/models/{HF_MODEL}", headers=headers, json=payload_hf, timeout=15)
            if not r.ok:
                errors.append(f"HF {HF_MODEL}: {r.status_code} {r.text}")
            else:
                try:
                    out = r.json()
                except ValueError:
                    errors.append("HF: invalid JSON response")
                else:
                    translated = None
                    if isinstance(out, list) and out:
                        translated = out[0].get("translation_text") or out[0].get("generated_text")
                    elif isinstance(out, dict):
                        translated = out.get("translation_text") or out.get("generated_text")
                    if translated:
                        return translated, None
                    else:
                        errors.append("HF: no translation_text in response")
        except requests.RequestException as e:
            errors.append(f"HF unreachable: {e}")

    # LibreTranslate fallbacks
    endpoints = [
        "https://libretranslate.de/translate",
        "https://libretranslate.com/translate",
        "https://translate.argosopentech.com/translate",
    ]
    payload = {"q": text, "source": source, "target": target, "format": "text"}
    for url in endpoints:
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        except requests.RequestException as e:
            errors.append(f"{url}: unreachable ({e})")
            continue
        if not response.ok:
            errors.append(f"{url}: {response.status_code} {response.text}")
            continue
        try:
            result = response.json()
        except ValueError:
            errors.append(f"{url}: invalid JSON body")
            continue
        translated = result.get("translatedText")
        if translated:
            return translated, None
        else:
            errors.append(f"{url}: no translatedText in response")

    # MyMemory fallback with chunking (skip if source auto)
    mymemory_codes = {
        "en": "en-GB", "ta": "ta-IN", "hi": "hi-IN", "te": "te-IN", "ml": "ml-IN", "kn": "kn-IN",
        "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN", "pa": "pa-IN", "ur": "ur-PK", "ar": "ar-SA",
        "fr": "fr-FR", "es": "es-ES", "de": "de-DE", "it": "it-IT", "pt": "pt-PT", "ru": "ru-RU",
        "zh": "zh-CN", "ja": "ja-JP", "ko": "ko-KR", "th": "th-TH", "vi": "vi-VN", "id": "id-ID",
        "tr": "tr-TR", "fa": "fa-IR", "he": "he-IL", "el": "el-GR", "nl": "nl-NL", "pl": "pl-PL",
        "sv": "sv-SE", "fi": "fi-FI", "no": "nb-NO", "da": "da-DK", "cs": "cs-CZ", "hu": "hu-HU",
        "ro": "ro-RO", "sk": "sk-SK", "uk": "uk-UA", "bg": "bg-BG", "hr": "hr-HR", "sr": "sr-Latn-RS",
        "sl": "sl-SI", "et": "et-EE", "lv": "lv-LV", "lt": "lt-LT", "ms": "ms-MY", "tl": "fil-PH",
        "sw": "sw-KE", "af": "af-ZA", "si": "si-LK", "ne": "ne-NP", "my": "my-MM", "hy": "hy-AM",
        "ca": "ca-ES", "km": "km-KH", "lo": "lo-LA", "as": "as-IN", "or": "or-IN", "sd": "sd-PK",
        "yo": "yo-NG", "ha": "ha-NE", "ig": "ig-NG", "xh": "xh-ZA", "zu": "zu-ZA",
    }
    mm_source = mymemory_codes.get(source)
    mm_target = mymemory_codes.get(target)

    def split_chunks(s, max_len=450):
        parts, current, length = [], [], 0
        for word in s.split():
            wlen = len(word) + (1 if length > 0 else 0)
            if length + wlen > max_len:
                parts.append(" ".join(current))
                current, length = [word], len(word)
            else:
                if length > 0:
                    current.append(word)
                    length += len(word) + 1
                else:
                    current, length = [word], len(word)
        if current:
            parts.append(" ".join(current))
        return parts

    if mm_source and mm_target and source != "auto":
        try:
            translator = MyMemoryTranslator(source=mm_source, target=mm_target)
            chunks = split_chunks(text)
            out_chunks = []
            for ch in chunks:
                tr = translator.translate(ch)
                if tr:
                    out_chunks.append(tr)
                else:
                    errors.append("MyMemory empty chunk")
            if out_chunks:
                return " ".join(out_chunks), None
        except Exception as e:
            errors.append(f"MyMemory failed: {e}")

    return None, "; ".join(errors) if errors else "Translation failed"

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

        with st.spinner("Translating..."):
            # Prefer backend if configured; otherwise use cloud providers directly
            translated = None
            error = None
            if API_BASE:
                api_url = f"{API_BASE}/translate"
                try:
                    response = requests.post(api_url, json=payload, timeout=30)
                    if response.ok:
                        data = response.json()
                        translated = data.get("translated_text", "")
                        if not translated:
                            error = "Backend returned no translated text."
                    else:
                        try:
                            err = response.json().get("detail")
                        except Exception:
                            err = response.text
                        error = f"Translation failed ({response.status_code}).\n{err}"
                except requests.RequestException:
                    # Backend unreachable → fall back to cloud providers
                    translated, error = cloud_translate(text, source_languages[source_name], target_languages[target_name])
            else:
                translated, error = cloud_translate(text, source_languages[source_name], target_languages[target_name])

            if translated:
                st.success("✅ Translated Text")
                st.code(translated)

                # Download translated text
                st.download_button("⬇️ Download Text", translated, file_name="translation.txt")

                # Text-to-speech for the translated output (target language only)
                supported_tts = tts_langs()
                tts_code_map = {"zh": "zh-CN", "tl": "fil", "no": "no"}
                tts_lang = tts_code_map.get(target_languages[target_name], target_languages[target_name])
                if tts_lang in supported_tts:
                    try:
                        tts = gTTS(text=translated, lang=tts_lang)
                        audio_buf = io.BytesIO()
                        tts.write_to_fp(audio_buf)
                        audio_buf.seek(0)
                        st.audio(audio_buf, format="audio/mp3")
                        st.download_button("🔊 Download Audio", audio_buf.getvalue(), file_name="translation.mp3", mime="audio/mpeg")
                    except Exception as e:
                        st.info(f"Speech not available for {target_name}: {e}")
                else:
                    st.info(f"Speech not supported for target language: {target_name}")
            else:
                st.error(error or "Translation failed")
