# Gold AI Advisor

A Python CLI assistant for gold (XAUUSD) trading. Combines:
- **Technicals**: EMA(20/100) trend stack, RSI(14), ADX(14) regime filter, ATR(14) — same indicator family as GreenCrowEA
- **Fundamentals**: DXY and 10Y Treasury yield momentum (gold's two dominant macro drivers), with a silver confluence check
- **Sentiment**: live gold-relevant news headlines (free RSS feeds), scored by Gemini
- **Chat**: free-text Q&A via the Gemini API, grounded in the latest forecast

## Two ways to run this

There are now two front ends sharing the same `core/` logic:
- **`streamlit_app.py`** — web dashboard, meant for GitHub + Streamlit Cloud deployment (see below)
- **`main.py`** — original terminal CLI, useful for quick local checks without spinning up a browser

## Local setup (either front end)

```bash
cd gold_ai_advisor
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your Gemini API key (free tier available at https://aistudio.google.com/apikey)
```

Run the CLI:
```bash
python main.py
```

Run the Streamlit app locally:
```bash
streamlit run streamlit_app.py
```
(Locally, `config.py` falls back to `.env` if no `.streamlit/secrets.toml` is found, so the same `.env` works for both front ends.)

Inside the CLI prompt:
- `/forecast` — pulls live price data, computes technicals, scores fundamentals, scrapes news, scores sentiment via Gemini, and prints a BUY/SELL/WAIT verdict with confidence %
- Anything else — sent to Gemini as a question, with the last forecast injected as context (e.g. "why is the sentiment score negative?", "should I widen my ATR stop given this regime?")
- `/exit` — quit

## Deploying to GitHub + Streamlit Community Cloud

1. **Push to GitHub.** The `.gitignore` already excludes `.env` and `.streamlit/secrets.toml`, so your API key won't accidentally get committed.
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Gold AI Advisor"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. **Create the app.** Go to https://share.streamlit.io, sign in with GitHub, click "New app", and point it at your repo with **`streamlit_app.py`** as the main file.
3. **Add your secret.** In the app's **Settings -> Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
   This is exactly the format in `.streamlit/secrets.toml.example`. `config.py` checks `st.secrets` first automatically — no code changes needed between local and deployed runs.
4. **Deploy.** Streamlit Cloud installs `requirements.txt` and runs the app. Every git push to `main` auto-redeploys.

Note on outbound access: Streamlit Cloud's containers can reach the public internet (Yahoo Finance, the RSS feeds, and the Gemini API all work fine there) — no extra network configuration needed on their end.

## Notes on data sources

- **Price data**: `yfinance`, free, no key required. `GC=F` (COMEX gold futures) is used as a free proxy for XAUUSD spot — they track almost 1:1 but can diverge slightly around futures roll dates and outside COMEX hours.
- **News**: free RSS feeds (Kitco, FXStreet, Investing.com, ForexLive). RSS feed URLs occasionally change or get restructured by the source site — if `/forecast` reports zero headlines, check `config.py -> NEWS_FEEDS` and swap in a working URL.
- **Fundamentals**: intentionally kept to two well-documented, programmatically-cheap drivers (USD strength, real yields) rather than trying to scrape a full economic calendar. The news/sentiment layer picks up Fed/CPI narrative that a pure price-based fundamental score would miss.

## Extending this

Natural next steps, in rough order of effort:
1. **Persist forecast history** to a CSV/SQLite so you can backtest the verdict signal itself, the same way you iterate on GreenCrowEA
2. **Feed a `/forecast` verdict into MT4/MT5** via a simple file-based bridge (write verdict + confidence to a CSV that an EA reads) or a local Flask endpoint your EA polls
3. **Add an economic calendar feed** (e.g. scraping a calendar page) for scheduled-event risk (NFP, CPI, FOMC) rather than only reactive news sentiment
4. **Swap Gemini model** in `.env` (`GEMINI_MODEL=gemini-2.5-pro`) if you want deeper reasoning on ambiguous setups, at higher latency/cost

## Project structure

```
gold_ai_advisor/
├── streamlit_app.py          # Streamlit dashboard (deploy this to Streamlit Cloud)
├── main.py                   # terminal CLI (local use)
├── config.py                 # tickers, weights, feeds, API key loading (env or st.secrets)
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
└── core/
    ├── gemini_client.py       # Gemini chat + sentiment scoring
    ├── market_data.py         # yfinance price fetching
    ├── technicals.py          # EMA/RSI/ADX/ATR + composite score
    ├── fundamentals.py        # DXY/yield/silver-confluence score
    ├── news_scraper.py        # RSS headline scraping + keyword filter
    └── aggregator.py          # weighted verdict (BUY/SELL/WAIT + confidence)
```
