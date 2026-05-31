import os
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

_client = None


def _get_client():
    global _client
    if not _client and ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_key_here":
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def analyze_news_sentiment(title: str, summary: str, related_tickers: list) -> dict:
    client = _get_client()
    if not client:
        return _fallback_sentiment(title)

    tickers_str = ", ".join(related_tickers) if related_tickers else "NASDAQ tech stocks generally"
    prompt = f"""Jsi expert na NASDAQ trading. Analyzuj tuto zprávu a její dopad na trh.

Zpráva: {title}
Detail: {summary[:500] if summary else 'N/A'}
Dotčené akcie: {tickers_str}

Odpověz POUZE v JSON formátu (reason piš česky, max 1 věta):
{{
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "strength": 1-5,
  "impact": "HIGH" | "MEDIUM" | "LOW",
  "reason": "jedno věta vysvětlení česky",
  "affected_tickers": ["seznam tickerů"],
  "action": "BUY_SIGNAL" | "SELL_SIGNAL" | "WATCH" | "IGNORE"
}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return _fallback_sentiment(title)


def analyze_macro_impact(event_name: str, value: float, change: float) -> dict:
    client = _get_client()
    if not client:
        return {"impact": "NEZNÁMÝ", "reason": "Přidej Anthropic API klíč pro AI analýzu"}

    prompt = f"""NASDAQ trader. Macro data released:
Event: {event_name}
Value: {value}
Change from previous: {change:+.3f}

JSON response only:
{{
  "nasdaq_impact": "BULLISH" | "BEARISH" | "NEUTRAL",
  "strength": 1-5,
  "reason": "one sentence",
  "sectors_affected": ["list of NASDAQ sectors"]
}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"impact": "UNKNOWN", "reason": "Analysis failed"}


def _fallback_sentiment(title: str) -> dict:
    title_lower = title.lower()
    if any(w in title_lower for w in ["beats", "surge", "rally", "growth", "record", "gain"]):
        sentiment = "BULLISH"
        action = "BUY_SIGNAL"
    elif any(w in title_lower for w in ["miss", "drop", "fall", "crash", "loss", "cut", "layoff"]):
        sentiment = "BEARISH"
        action = "SELL_SIGNAL"
    else:
        sentiment = "NEUTRAL"
        action = "WATCH"
    return {
        "sentiment": sentiment,
        "strength": 2,
        "impact": "MEDIUM",
        "reason": "Analýza podle klíčových slov (přidej Anthropic API klíč pro AI)",
        "affected_tickers": [],
        "action": action,
    }
