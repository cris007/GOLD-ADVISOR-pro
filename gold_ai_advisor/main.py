"""
Gold AI Advisor - CLI entrypoint.

Usage:
    python main.py

Commands inside the loop:
    /forecast   - run a full technical + fundamental + sentiment forecast
    /refresh    - force-refresh cached market data and news on next forecast
    /exit       - quit

Anything else you type is sent to Gemini as a free-text question, with the
most recent forecast (if any) injected as grounding context.
"""
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core import market_data, technicals, fundamentals, news_scraper, gemini_client, aggregator

console = Console()

_last_context = "No forecast has been run yet this session. Run /forecast first for live data."
_chat_history = []


def run_forecast() -> str:
    console.print("[dim]Fetching price data (gold, DXY, 10Y yield, silver)...[/dim]")
    data = market_data.fetch_all(period="6mo", interval="1d")

    console.print("[dim]Computing technicals...[/dim]")
    tech = technicals.analyze(data.get("gold"))

    console.print("[dim]Scoring fundamentals (DXY / yields / silver confluence)...[/dim]")
    fund = fundamentals.analyze(data)

    console.print("[dim]Scraping gold-relevant news headlines...[/dim]")
    headlines = news_scraper.fetch_headlines()

    console.print(f"[dim]Scoring sentiment on {len(headlines)} headlines via Gemini...[/dim]")
    sent = gemini_client.score_headlines_sentiment([h["title"] for h in headlines])

    verdict = aggregator.build_verdict(tech, fund, sent)

    # --- Render ---
    table = Table(title="Gold (XAUUSD) Forecast Snapshot", show_header=True, header_style="bold yellow")
    table.add_column("Layer")
    table.add_column("Read")
    table.add_column("Score")

    if "error" not in tech:
        table.add_row(
            "Technical",
            f"price {tech['price']} | EMA{20}/{100}: {tech['ema_fast']}/{tech['ema_slow']} | "
            f"RSI {tech['rsi']} | ADX {tech['adx']} ({tech['regime']})",
            str(tech["score"]),
        )
    else:
        table.add_row("Technical", tech["error"], "-")

    if "error" not in fund:
        table.add_row("Fundamental", " | ".join(fund["notes"]) or "neutral", str(fund["score"]))
    else:
        table.add_row("Fundamental", fund["error"], "-")

    table.add_row("Sentiment", sent.get("rationale", ""), str(sent.get("score", 0.0)))

    console.print(table)
    console.print(
        Panel(
            f"[bold]{verdict['verdict']}[/bold]  (confidence: {verdict['confidence_pct']}%, "
            f"composite score: {verdict['composite_score']})",
            title="Verdict",
            border_style="green" if verdict["verdict"] == "BUY" else ("red" if verdict["verdict"] == "SELL" else "yellow"),
        )
    )

    if headlines:
        console.print("[bold]Top headlines used:[/bold]")
        for h in headlines[:8]:
            console.print(f"  - [{h['source']}] {h['title']}")

    # Build a compact context string for Gemini chat grounding
    context = (
        f"Technical: {tech}\n"
        f"Fundamental: {fund}\n"
        f"Sentiment: {sent}\n"
        f"Verdict: {verdict}\n"
        f"Recent headlines: {[h['title'] for h in headlines[:10]]}"
    )
    return context


def main():
    global _last_context, _chat_history

    console.print(Panel(
        "Gold AI Advisor - type /forecast to run a full analysis, or ask anything.\n"
        "Type /exit to quit.",
        title="Welcome", border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]> [/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            sys.exit(0)

        if not user_input:
            continue
        if user_input.lower() in ("/exit", "/quit"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if user_input.lower() == "/forecast":
            try:
                _last_context = run_forecast()
            except Exception as e:
                console.print(f"[red]Forecast failed: {e}[/red]")
            continue
        if user_input.lower() == "/refresh":
            console.print("[dim]Next /forecast call will pull fresh data (no persistent cache to clear currently).[/dim]")
            continue

        # Otherwise: free-text question to Gemini, grounded in last forecast
        try:
            reply = gemini_client.chat(user_input, _last_context, history=_chat_history)
            console.print(f"\n[bold magenta]Gemini:[/bold magenta] {reply}")
            _chat_history.append({"role": "user", "parts": [user_input]})
            _chat_history.append({"role": "model", "parts": [reply]})
        except Exception as e:
            console.print(f"[red]Chat failed: {e}[/red]")


if __name__ == "__main__":
    main()
