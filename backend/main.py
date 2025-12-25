from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from deep_translator import MyMemoryTranslator

load_dotenv()

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv("HUGGINGFACE_MODEL", "facebook/m2m100_418M")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

app = FastAPI()

# Allow Streamlit (localhost:8501) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all during local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

# Public list of supported language codes and names
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
    "ka": "Georgian",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "la": "Latin",
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

@app.post("/translate")
def translate_text(data: TranslateRequest):
    errors = []

    # Try Hugging Face Inference API first if API key is set and source is not auto
    if HF_API_KEY and data.source_lang != "auto":
        try:
            headers = {
                "Authorization": f"Bearer {HF_API_KEY}",
                "Content-Type": "application/json",
            }
            payload_hf = {
                "inputs": data.text,
                "parameters": {"src_lang": data.source_lang, "tgt_lang": data.target_lang},
            }
            r = requests.post(HF_API_URL, headers=headers, json=payload_hf, timeout=15)
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
                        return {"translated_text": translated}
                    else:
                        errors.append("HF: no translation_text in response")
        except requests.RequestException as e:
            errors.append(f"HF unreachable: {e}")

    endpoints = [
        "https://libretranslate.de/translate",
        "https://libretranslate.com/translate",
        "https://translate.argosopentech.com/translate",
    ]

    payload = {
        "q": data.text,
        "source": data.source_lang,
        "target": data.target_lang,
        "format": "text",
    }

    for url in endpoints:
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
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
            return {"translated_text": translated}
        else:
            errors.append(f"{url}: no translatedText in response")

    # Fallback: use MyMemory free translator
    # MyMemory expects locale-style codes (e.g., en-GB, fr-FR)
    mymemory_codes = {
        "en": "en-GB",
        "ta": "ta-IN",
        "hi": "hi-IN",
        "te": "te-IN",
        "ml": "ml-IN",
        "kn": "kn-IN",
        "mr": "mr-IN",
        "bn": "bn-IN",
        "gu": "gu-IN",
        "pa": "pa-IN",
        "ur": "ur-PK",
        "ar": "ar-SA",
        "fr": "fr-FR",
        "es": "es-ES",
        "de": "de-DE",
        "it": "it-IT",
        "pt": "pt-PT",
        "ru": "ru-RU",
        "zh": "zh-CN",
        "ja": "ja-JP",
        "ko": "ko-KR",
        "th": "th-TH",
        "vi": "vi-VN",
        "id": "id-ID",
        "tr": "tr-TR",
        "fa": "fa-IR",
        "he": "he-IL",
        "el": "el-GR",
        "nl": "nl-NL",
        "pl": "pl-PL",
        "sv": "sv-SE",
        "fi": "fi-FI",
        "no": "nb-NO",
        "da": "da-DK",
        "cs": "cs-CZ",
        "hu": "hu-HU",
        "ro": "ro-RO",
        "sk": "sk-SK",
        "uk": "uk-UA",
        "bg": "bg-BG",
        "hr": "hr-HR",
        "sr": "sr-Latn-RS",
        "sl": "sl-SI",
        "et": "et-EE",
        "lv": "lv-LV",
        "lt": "lt-LT",
        "ms": "ms-MY",
        "tl": "fil-PH",
        "sw": "sw-KE",
        "af": "af-ZA",
        "si": "si-LK",
        "ne": "ne-NP",
        "my": "my-MM",
        "hy": "hy-AM",
        "ca": "ca-ES",
        "km": "km-KH",
        "lo": "lo-LA",
        "as": "as-IN",
        "or": "or-IN",
        "sd": "sd-PK",
        "yo": "yo-NG",
        "ha": "ha-NE",
        "ig": "ig-NG",
        "xh": "xh-ZA",
        "zu": "zu-ZA",
    }

    mm_source = mymemory_codes.get(data.source_lang)
    mm_target = mymemory_codes.get(data.target_lang)

    def _split_text_chunks(text: str, max_len: int = 450):
        # Word-safe chunking, prefer sentence boundaries
        parts = []
        current = []
        length = 0
        # First split by whitespace, keep punctuation
        for word in text.split():
            wlen = len(word) + (1 if length > 0 else 0)
            if length + wlen > max_len:
                parts.append(" ".join(current))
                current = [word]
                length = len(word)
            else:
                if length > 0:
                    current.append(word)
                    length += len(word) + 1
                else:
                    current = [word]
                    length = len(word)
        if current:
            parts.append(" ".join(current))
        return parts

    # Skip MyMemory if codes unsupported or source is auto
    if mm_target and mm_source and data.source_lang != "auto":
        try:
            translator = MyMemoryTranslator(source=mm_source, target=mm_target)
            chunks = _split_text_chunks(data.text, max_len=450)
            translated_chunks = []
            for ch in chunks:
                tr = translator.translate(ch)
                if not tr:
                    errors.append("MyMemory returned empty for a chunk")
                    continue
                translated_chunks.append(tr)
            if translated_chunks:
                return {"translated_text": " ".join(translated_chunks)}
        except Exception as e:
            errors.append(f"MyMemory fallback failed: {e}")

    raise HTTPException(status_code=502, detail="; ".join(errors) or "Translation failed")

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/languages")
def list_languages():
    # Return sorted language list as [{code, name}]
    items = [{"code": code, "name": LANGUAGE_NAMES.get(code, code)} for code in sorted(set([
        "af","ar","as","bg","bn","ca","cs","da","de","el","en","es","et","fa","fi","fr","gu","ha","he","hi","hr","hu","hy","id","ig","it","ja","km","kn","ko","lo","lt","lv","ml","mr","ms","my","nb","ne","nl","no","or","pa","pl","pt","ro","ru","sd","si","sk","sl","sr","sv","sw","ta","te","th","tl","tr","uk","ur","vi","yo","zh","zu","xh"
    ]) )]
    return {"languages": items}
