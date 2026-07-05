"""
Pulls recent headlines from free financial RSS feeds and filters them
for gold-relevant keywords. No API key required.

Note: RSS feed availability/structure can change over time. If a feed starts
returning nothing, check its URL still resolves in a browser and swap it out
in config.NEWS_FEEDS - this module degrades gracefully (skips dead feeds).
"""
import feedparser
from config import NEWS_FEEDS, NEWS_KEYWORDS, MAX_HEADLINES


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in NEWS_KEYWORDS)


def fetch_headlines() -> list[dict]:
    """Returns a list of {"title": ..., "link": ..., "published": ..., "source": ...} dicts."""
    headlines = []
    for feed_url in NEWS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.bozo and not parsed.entries:
                print(f"[news_scraper] Warning: could not parse feed {feed_url}")
                continue
            for entry in parsed.entries:
                title = getattr(entry, "title", "")
                if not title or not _is_relevant(title):
                    continue
                headlines.append({
                    "title": title.strip(),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                    "source": parsed.feed.get("title", feed_url),
                })
        except Exception as e:
            print(f"[news_scraper] Error fetching {feed_url}: {e}")
            continue

    # de-duplicate by title, most recent feeds first, cap the count
    seen = set()
    unique = []
    for h in headlines:
        key = h["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return unique[:MAX_HEADLINES]


if __name__ == "__main__":
    for h in fetch_headlines():
        print(f"- [{h['source']}] {h['title']}")
