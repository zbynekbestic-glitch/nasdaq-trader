from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")

import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

import asyncio
import json
import os
from datetime import datetime
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from data.stocks import get_all_fundamentals, get_price_history
from data.macro import get_macro_data, get_upcoming_events
from data.news import get_all_news
from data.ai_analysis import analyze_news_sentiment, analyze_macro_impact

app = FastAPI(title="NASDAQ Fundamental Trader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/sw.js")
async def service_worker():
    from fastapi.responses import FileResponse as FR
    return FR(os.path.join(frontend_path, "sw.js"), media_type="application/javascript")

# In-memory cache
_cache = {
    "fundamentals": [],
    "macro": [],
    "news": [],
    "alerts": [],
    "last_update": None,
}

# WebSocket clients
_clients: Set[WebSocket] = set()


async def broadcast(message: dict):
    global _clients
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send_json(message)
        except:
            dead.add(ws)
    _clients -= dead


async def refresh_fundamentals():
    data = get_all_fundamentals()
    _cache["fundamentals"] = data
    await broadcast({"type": "fundamentals", "data": data})


async def refresh_news():
    articles = get_all_news()
    enriched = []
    for art in articles[:15]:  # AI analýza jen pro top 15
        sentiment = analyze_news_sentiment(
            art["title"], art["summary"], art["related_tickers"]
        )
        art["ai"] = sentiment

        # Vytvoř alert pro vysoký dopad
        if sentiment.get("impact") == "HIGH" or art.get("is_breaking"):
            alert = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "title": art["title"],
                "sentiment": sentiment.get("sentiment", "NEUTRAL"),
                "action": sentiment.get("action", "WATCH"),
                "tickers": sentiment.get("affected_tickers", []),
                "source": art["source"],
            }
            _cache["alerts"].insert(0, alert)
            _cache["alerts"] = _cache["alerts"][:20]  # max 20 alertů
            await broadcast({"type": "alert", "data": alert})

        enriched.append(art)

    _cache["news"] = enriched
    _cache["last_update"] = datetime.now().isoformat()
    await broadcast({"type": "news", "data": enriched})


async def refresh_macro():
    data = get_macro_data()
    enriched = []
    for item in data:
        if item.get("change") is not None and not item.get("error"):
            ai = analyze_macro_impact(item["name"], item.get("value", 0), item.get("change", 0))
            item["ai"] = ai
        enriched.append(item)
    _cache["macro"] = enriched
    await broadcast({"type": "macro", "data": enriched})


@app.on_event("startup")
async def startup():
    # Scheduler — spustí se hned
    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_fundamentals, "interval", minutes=5, id="fundamentals", next_run_time=datetime.now())
    scheduler.add_job(refresh_news, "interval", minutes=2, id="news", next_run_time=datetime.now())
    scheduler.add_job(refresh_macro, "interval", minutes=30, id="macro", next_run_time=datetime.now())
    scheduler.start()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    # Pošli aktuální cache hned po připojení
    await ws.send_json({"type": "fundamentals", "data": _cache["fundamentals"]})
    await ws.send_json({"type": "news", "data": _cache["news"]})
    await ws.send_json({"type": "macro", "data": _cache["macro"]})
    await ws.send_json({"type": "alerts", "data": _cache["alerts"]})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _clients.discard(ws)


@app.get("/api/fundamentals")
async def api_fundamentals():
    return _cache["fundamentals"]


@app.get("/api/news")
async def api_news():
    return _cache["news"]


@app.get("/api/macro")
async def api_macro():
    return _cache["macro"]


@app.get("/api/alerts")
async def api_alerts():
    return _cache["alerts"]


@app.get("/api/chart/{ticker}")
async def api_chart(ticker: str, period: str = "1d", interval: str = "5m"):
    return get_price_history(ticker, period, interval)


@app.get("/api/events")
async def api_events():
    return get_upcoming_events()


@app.get("/api/refresh")
async def api_refresh():
    asyncio.create_task(refresh_news())
    asyncio.create_task(refresh_fundamentals())
    return {"status": "refreshing"}


@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))
