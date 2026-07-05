"""
Thin wrapper around the Google Gemini API.
Used for two things:
  1. Scoring the sentiment of scraped headlines (structured JSON output)
  2. Answering the user's free-text prompts, grounded in the latest forecast context
"""
import json
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

_configured = False


def _ensure_configured():
    global _configured
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set.\n"
            "- Local CLI: create a .env file in the project root with GEMINI_API_KEY=your_key_here\n"
            "- Streamlit Cloud: add GEMINI_API_KEY under Settings -> Secrets\n"
            "Get a free key at https://aistudio.google.com/apikey"
        )
    if not _configured:
        genai.configure(api_key=GEMINI_API_KEY)
        _configured = True


def score_headlines_sentiment(headlines: list[str]) -> dict:
    """
    Sends headlines to Gemini and asks for a single aggregate sentiment score
    for gold in [-1, +1], plus a one-line rationale. Returns a safe default on failure.
    """
    if not headlines:
        return {"score": 0.0, "rationale": "No relevant headlines found."}

    _ensure_configured()
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = (
        "You are a financial news sentiment analyst focused on gold (XAUUSD).\n"
        "Given these recent headlines, output ONLY a JSON object (no markdown fences, "
        "no preamble) with exactly these keys:\n"
        '{"score": <float from -1.0 (very bearish for gold) to 1.0 (very bullish for gold)>, '
        '"rationale": "<one sentence explaining the score>"}\n\n'
        "Headlines:\n" + "\n".join(f"- {h}" for h in headlines)
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        score = max(-1.0, min(1.0, float(parsed.get("score", 0.0))))
        return {"score": round(score, 3), "rationale": parsed.get("rationale", "")}
    except Exception as e:
        print(f"[gemini_client] Sentiment scoring failed: {e}")
        return {"score": 0.0, "rationale": "Sentiment scoring unavailable (API error)."}


def chat(user_prompt: str, market_context: str, history: list[dict] | None = None) -> str:
    """
    Answers a free-text prompt, grounded in the current market_context string
    (built by main.py from the latest forecast). `history` is a list of
    {"role": "user"/"model", "parts": [text]} dicts for multi-turn continuity.
    """
    _ensure_configured()
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=(
            "You are a gold (XAUUSD) trading assistant for an experienced algorithmic trader "
            "who builds his own MT4/MT5 Expert Advisors. Be direct and concrete. Reference the "
            "live market context provided below when relevant. Do not give financial advice "
            "disclaimers unless the user is making an unusually risky decision - this user is "
            "an experienced professional. Keep answers focused and avoid padding.\n\n"
            f"CURRENT MARKET CONTEXT:\n{market_context}"
        ),
    )
    chat_session = model.start_chat(history=history or [])
    try:
        response = chat_session.send_message(user_prompt)
        return response.text
    except Exception as e:
        return f"[gemini_client] Error contacting Gemini API: {e}"
