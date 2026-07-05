st.sidebar.write("Key loaded:", bool(st.secrets.get("GEMINI_API_KEY", "")))
"""
Gold AI Advisor - Streamlit app.

Deploy on Streamlit Community Cloud:
1. Push this repo to GitHub.
2. On https://share.streamlit.io, create a new app pointing at streamlit_app.py.
3. In the app's Settings -> Secrets, add:
       GEMINI_API_KEY = "your_key_here"
4. Deploy. No .env file is needed in production - config.py reads st.secrets automatically.

Local dev: `streamlit run streamlit_app.py` (uses .env via python-dotenv, same as the CLI).
"""
import streamlit as st

from core import market_data, technicals, fundamentals, news_scraper, gemini_client, aggregator

st.set_page_config(page_title="Gold AI Advisor", page_icon="🥇", layout="wide")

# --- Session state ---
if "context" not in st.session_state:
    st.session_state.context = "No forecast has been run yet. Click 'Run Forecast' in the sidebar."
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": "user"/"model", "parts": [text]}
if "last_forecast" not in st.session_state:
    st.session_state.last_forecast = None


def run_forecast():
    with st.spinner("Fetching price data..."):
        data = market_data.fetch_all(period="6mo", interval="1d")
    with st.spinner("Computing technicals..."):
        tech = technicals.analyze(data.get("gold"))
    with st.spinner("Scoring fundamentals..."):
        fund = fundamentals.analyze(data)
    with st.spinner("Scraping gold-relevant news..."):
        headlines = news_scraper.fetch_headlines()
    with st.spinner(f"Scoring sentiment on {len(headlines)} headlines via Gemini..."):
        sent = gemini_client.score_headlines_sentiment([h["title"] for h in headlines])

    verdict = aggregator.build_verdict(tech, fund, sent)

    st.session_state.last_forecast = {
        "tech": tech, "fund": fund, "sent": sent, "verdict": verdict, "headlines": headlines,
    }
    st.session_state.context = (
        f"Technical: {tech}\nFundamental: {fund}\nSentiment: {sent}\nVerdict: {verdict}\n"
        f"Recent headlines: {[h['title'] for h in headlines[:10]]}"
    )


# --- Sidebar ---
with st.sidebar:
    st.title("🥇 Gold AI Advisor")
    st.caption("Technical + fundamental + sentiment confluence, powered by Gemini.")
    if st.button("🔄 Run Forecast", use_container_width=True, type="primary"):
        run_forecast()
    st.divider()
    st.caption(
        "Data sources: yfinance (GC=F, DXY, ^TNX, silver) for price/macro data; "
        "free RSS feeds (Kitco, FXStreet, Investing.com, ForexLive) for news."
    )

# --- Main layout ---
st.title("Gold (XAUUSD) Forecast Dashboard")

fc = st.session_state.last_forecast
if fc is None:
    st.info("Click **Run Forecast** in the sidebar to pull live data and generate a verdict.")
else:
    tech, fund, sent, verdict, headlines = fc["tech"], fc["fund"], fc["sent"], fc["verdict"], fc["headlines"]

    verdict_color = {"BUY": "green", "SELL": "red", "WAIT": "orange"}[verdict["verdict"]]
    st.markdown(
        f"### Verdict: :{verdict_color}[{verdict['verdict']}]  "
        f"— confidence {verdict['confidence_pct']}%  (composite score {verdict['composite_score']})"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Technical")
        if "error" not in tech:
            st.metric("Price", tech["price"])
            st.write(f"EMA20 / EMA100: {tech['ema_fast']} / {tech['ema_slow']}")
            st.write(f"RSI(14): {tech['rsi']}  |  ADX(14): {tech['adx']} ({tech['regime']})")
            st.write(f"ATR(14): {tech['atr']}")
            st.metric("Score", tech["score"])
        else:
            st.warning(tech["error"])
    with col2:
        st.subheader("Fundamental")
        if "error" not in fund:
            for note in fund["notes"]:
                st.write(f"- {note}")
            st.write(f"Silver confluence: {fund['silver_confluence']}")
            st.metric("Score", fund["score"])
        else:
            st.warning(fund["error"])
    with col3:
        st.subheader("Sentiment")
        st.write(sent.get("rationale", ""))
        st.metric("Score", sent.get("score", 0.0))

    if headlines:
        with st.expander(f"Headlines used ({len(headlines)})"):
            for h in headlines:
                st.write(f"**[{h['source']}]** {h['title']}")

st.divider()
st.subheader("Ask the advisor")
st.caption("Grounded in the latest forecast above. Run a forecast first for live-data answers.")

for msg in st.session_state.chat_history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(msg["parts"][0])

user_prompt = st.chat_input("Ask about the current setup, risk, or what would change the verdict...")
if user_prompt:
    st.session_state.chat_history.append({"role": "user", "parts": [user_prompt]})
    with st.chat_message("user"):
        st.write(user_prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = gemini_client.chat(
                user_prompt,
                st.session_state.context,
                history=st.session_state.chat_history[:-1],  # exclude the message just sent
            )
        st.write(reply)
    st.session_state.chat_history.append({"role": "model", "parts": [reply]})
