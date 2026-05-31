import requests
import os
import time
from datetime import datetime

WATCHLIST = os.getenv("WATCHLIST", "AAPL,NVDA,META,MSFT,AMZN,GOOGL,TSLA,AMD,INTC,SMCI").split(",")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}

_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        try:
            import certifi
            _session.verify = certifi.where()
        except Exception:
            pass
        # Get crumb cookie
        try:
            _session.get("https://finance.yahoo.com/quote/AAPL", timeout=5)
        except Exception:
            pass
    return _session


def _yahoo_quote(ticker: str) -> dict:
    s = _get_session()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    try:
        r = s.get(url, timeout=8)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        return {
            "price": meta.get("regularMarketPrice"),
            "prev_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
            "52w_high": meta.get("fiftyTwoWeekHigh"),
            "52w_low": meta.get("fiftyTwoWeekLow"),
            "volume": meta.get("regularMarketVolume"),
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        return {}


def _yahoo_fundamentals(ticker: str) -> dict:
    s = _get_session()
    modules = "financialData,defaultKeyStatistics,summaryDetail,assetProfile,price"
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules}"
    try:
        r = s.get(url, timeout=8)
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return {}
        res = result[0]
        fd = res.get("financialData", {})
        ks = res.get("defaultKeyStatistics", {})
        sd = res.get("summaryDetail", {})
        pr = res.get("price", {})
        ap = res.get("assetProfile", {})
        return {
            "name": pr.get("longName", {}).get("raw") if isinstance(pr.get("longName"), dict) else pr.get("longName"),
            "pe_ratio": sd.get("trailingPE", {}).get("raw") if isinstance(sd.get("trailingPE"), dict) else sd.get("trailingPE"),
            "forward_pe": ks.get("forwardPE", {}).get("raw") if isinstance(ks.get("forwardPE"), dict) else ks.get("forwardPE"),
            "eps": ks.get("trailingEps", {}).get("raw") if isinstance(ks.get("trailingEps"), dict) else ks.get("trailingEps"),
            "eps_next_quarter": ks.get("forwardEps", {}).get("raw") if isinstance(ks.get("forwardEps"), dict) else ks.get("forwardEps"),
            "revenue_growth": fd.get("revenueGrowth", {}).get("raw") if isinstance(fd.get("revenueGrowth"), dict) else fd.get("revenueGrowth"),
            "earnings_growth": fd.get("earningsGrowth", {}).get("raw") if isinstance(fd.get("earningsGrowth"), dict) else fd.get("earningsGrowth"),
            "profit_margin": fd.get("profitMargins", {}).get("raw") if isinstance(fd.get("profitMargins"), dict) else fd.get("profitMargins"),
            "debt_to_equity": fd.get("debtToEquity", {}).get("raw") if isinstance(fd.get("debtToEquity"), dict) else fd.get("debtToEquity"),
            "free_cashflow": fd.get("freeCashflow", {}).get("raw") if isinstance(fd.get("freeCashflow"), dict) else fd.get("freeCashflow"),
            "market_cap": pr.get("marketCap", {}).get("raw") if isinstance(pr.get("marketCap"), dict) else pr.get("marketCap"),
            "analyst_target": fd.get("targetMeanPrice", {}).get("raw") if isinstance(fd.get("targetMeanPrice"), dict) else fd.get("targetMeanPrice"),
            "recommendation": fd.get("recommendationKey"),
            "sector": ap.get("sector"),
            "avg_volume": sd.get("averageVolume", {}).get("raw") if isinstance(sd.get("averageVolume"), dict) else sd.get("averageVolume"),
        }
    except Exception:
        return {}


def get_fundamentals(ticker: str) -> dict:
    ticker = ticker.strip()
    try:
        quote = _yahoo_quote(ticker)
        fund = _yahoo_fundamentals(ticker)

        price = quote.get("price")
        prev_close = quote.get("prev_close")
        change_pct = round(((price - prev_close) / prev_close) * 100, 2) if price and prev_close else 0.0

        return {
            "ticker": ticker,
            "name": fund.get("name") or ticker,
            "price": price,
            "change_pct": change_pct,
            "market_cap": fund.get("market_cap"),
            "pe_ratio": fund.get("pe_ratio"),
            "forward_pe": fund.get("forward_pe"),
            "eps": fund.get("eps"),
            "eps_next_quarter": fund.get("eps_next_quarter"),
            "revenue_growth": fund.get("revenue_growth"),
            "earnings_growth": fund.get("earnings_growth"),
            "profit_margin": fund.get("profit_margin"),
            "debt_to_equity": fund.get("debt_to_equity"),
            "free_cashflow": fund.get("free_cashflow"),
            "analyst_target": fund.get("analyst_target"),
            "recommendation": fund.get("recommendation"),
            "sector": fund.get("sector"),
            "52w_high": quote.get("52w_high"),
            "52w_low": quote.get("52w_low"),
            "volume": quote.get("volume"),
            "avg_volume": fund.get("avg_volume"),
            "updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_all_fundamentals() -> list:
    results = []
    for ticker in WATCHLIST:
        results.append(get_fundamentals(ticker.strip()))
        time.sleep(0.8)
    return results


def get_price_history(ticker: str, period: str = "1d", interval: str = "5m") -> list:
    s = _get_session()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={period}"
    try:
        r = s.get(url, timeout=8)
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        opens = result["indicators"]["quote"][0]["open"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        volumes = result["indicators"]["quote"][0]["volume"]
        return [
            {
                "time": datetime.fromtimestamp(timestamps[i]).isoformat(),
                "open": opens[i],
                "high": highs[i],
                "low": lows[i],
                "close": closes[i],
                "volume": volumes[i],
            }
            for i in range(len(timestamps)) if closes[i] is not None
        ]
    except Exception:
        return []
