import requests
import feedparser
import os
from datetime import datetime, timezone

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# RSS feeds - zdarma, bez API klíče
RSS_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC Markets", "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Seeking Alpha", "https://seekingalpha.com/feed.xml"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Investing.com", "https://www.investing.com/rss/news.rss"),
]

# Klíčová slova pro market-moving události
MARKET_MOVING_KEYWORDS = [
    "trump", "fed", "federal reserve", "interest rate", "inflation", "tariff",
    "earnings", "revenue", "guidance", "nvidia", "apple", "microsoft", "meta",
    "alphabet", "amazon", "tesla", "semiconductor", "ai", "artificial intelligence",
    "chip", "ban", "sanction", "recession", "gdp", "unemployment", "jobs",
    "powell", "yellen", "sec", "antitrust", "regulation", "china", "taiwan",
    "war", "geopolit", "opec", "oil", "rate cut", "rate hike", "fomc",
]

NASDAQ_STOCKS = os.getenv("WATCHLIST", "AAPL,NVDA,META,MSFT,AMZN,GOOGL,TSLA,AMD,INTC,SMCI").split(",")


def fetch_rss_news(max_per_feed: int = 10) -> list:
    articles = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                impact_score, matched_keywords, related_tickers = _analyze_relevance(title + " " + summary)

                if impact_score > 0:
                    articles.append({
                        "title": title,
                        "summary": summary[:300] if summary else "",
                        "url": link,
                        "source": source_name,
                        "published": published,
                        "impact_score": impact_score,
                        "keywords": matched_keywords,
                        "related_tickers": related_tickers,
                        "sentiment": None,  # vyplní AI analýza
                        "is_breaking": impact_score >= 3,
                    })
        except Exception:
            continue

    articles.sort(key=lambda x: x["impact_score"], reverse=True)
    return articles[:50]


def fetch_newsapi(query: str = "NASDAQ stocks market") -> list:
    if not NEWS_API_KEY or NEWS_API_KEY == "your_key_here":
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": NEWS_API_KEY,
            },
            timeout=5,
        )
        data = resp.json()
        articles = []
        for art in data.get("articles", []):
            title = art.get("title", "")
            description = art.get("description", "")
            impact_score, keywords, tickers = _analyze_relevance(title + " " + description)
            articles.append({
                "title": title,
                "summary": description,
                "url": art.get("url", ""),
                "source": art.get("source", {}).get("name", ""),
                "published": art.get("publishedAt", ""),
                "impact_score": impact_score,
                "keywords": keywords,
                "related_tickers": tickers,
                "sentiment": None,
                "is_breaking": impact_score >= 3,
            })
        return articles
    except:
        return []


def _analyze_relevance(text: str) -> tuple:
    text_lower = text.lower()
    matched = [kw for kw in MARKET_MOVING_KEYWORDS if kw in text_lower]
    related_tickers = [t.strip() for t in NASDAQ_STOCKS if t.strip().lower() in text_lower]

    score = len(matched)
    if related_tickers:
        score += len(related_tickers) * 2
    if any(kw in text_lower for kw in ["trump", "fed", "fomc", "rate"]):
        score += 2
    if any(kw in text_lower for kw in ["breaking", "urgent", "alert", "just in"]):
        score += 3

    return score, matched[:5], related_tickers


def get_all_news() -> list:
    rss = fetch_rss_news()
    api = fetch_newsapi("NASDAQ tech stocks AI earnings")
    combined = rss + api
    combined.sort(key=lambda x: x["impact_score"], reverse=True)
    seen = set()
    unique = []
    for art in combined:
        if art["title"] not in seen:
            seen.add(art["title"])
            unique.append(art)
    return unique[:40]
