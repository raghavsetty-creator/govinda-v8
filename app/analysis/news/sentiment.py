"""
NIFTY AI Trading System — News Sentiment Analyzer
===================================================
Fetches and scores news from multiple sources:
- Economic Times Markets RSS
- MoneyControl RSS  
- NSE announcements
- Google Finance news
- Reddit (r/IndiaInvestments)

Scores sentiment and predicts market impact.
"""

import requests
import feedparser
import json
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from knowledge.market_knowledge import classify_news_impact, NEWS_IMPACT

logger = logging.getLogger(__name__)


# VADER for financial sentiment
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER = SentimentIntensityAnalyzer()
    # Add finance-specific words to VADER
    VADER.lexicon.update({
        "bullish": 3.0, "bearish": -3.0, "rally": 2.5, "surge": 2.5,
        "crash": -3.5, "plunge": -3.0, "soar": 3.0, "tumble": -2.5,
        "rbi": 0.0, "nifty": 0.0, "sensex": 0.0, "fii": 1.0,
        "outperform": 2.0, "downgrade": -2.0, "upgrade": 2.0,
        "rate hike": -2.0, "rate cut": 2.5, "default": -3.0,
        "buyback": 2.0, "dividend": 1.5, "bonus": 1.5,
        "npa": -1.5, "fraud": -3.5, "scam": -3.5, "penalty": -2.0,
    })
    HAS_VADER = True
except ImportError:
    HAS_VADER = False
    logger.warning("VADER not available, using basic sentiment")


NEWS_SOURCES = {
    "economic_times": {
        "name": "Economic Times",
        "rss":  "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "weight": 1.5,
    },
    "moneycontrol": {
        "name": "MoneyControl",
        "rss":  "https://www.moneycontrol.com/rss/latestnews.xml",
        "weight": 1.3,
    },
    "nse_announcements": {
        "name": "NSE Corporate Announcements",
        "rss":  "https://nsearchives.nseindia.com/corporate/anndet.xml",
        "weight": 2.0,
    },
    "livemint": {
        "name": "LiveMint Markets",
        "rss":  "https://www.livemint.com/rss/markets",
        "weight": 1.2,
    },
    "business_standard": {
        "name": "Business Standard",
        "rss":  "https://www.business-standard.com/rss/markets-106.rss",
        "weight": 1.2,
    },
}

# Keywords that directly impact NIFTY
NIFTY_KEYWORDS = {
    "high_positive": [
        "rate cut", "gdp beats", "stimulus", "record profit", "fii buying",
        "trade surplus", "inflation cools", "strong gdp", "market rally",
        "buyback", "bonus issue", "major order", "export growth"
    ],
    "moderate_positive": [
        "earnings beat", "revenue growth", "profit growth", "positive outlook",
        "upgrade", "dovish", "inflation stable", "credit growth"
    ],
    "high_negative": [
        "rate hike", "inflation surge", "recession", "market crash", "war",
        "default", "crisis", "sanctions", "fii selling", "fraud", "scam",
        "global selloff", "fed hawkish", "oil surge"
    ],
    "moderate_negative": [
        "profit miss", "revenue decline", "downgrade", "negative outlook",
        "hawkish", "slowdown", "layoffs", "npa rise"
    ],
    "event_driven": [
        "rbi policy", "fed meeting", "union budget", "election results",
        "quarterly results", "cpi data", "gdp data", "iip data"
    ],
}


class NewsSentimentAnalyzer:
    """
    Multi-source news aggregator with NIFTY impact scoring.
    """

    def __init__(self):
        self.news_cache      = []
        self.last_fetch_time = None
        self.cache_duration  = 15  # minutes

    def get_market_sentiment(self) -> dict:
        """
        Main method — fetches news and returns comprehensive sentiment report.
        """
        news_items = self._fetch_all_news()

        if not news_items:
            return self._empty_sentiment()

        scored_news = [self._score_news_item(item) for item in news_items]
        scored_news.sort(key=lambda x: abs(x["impact_score"]), reverse=True)

        # Aggregate scores
        total_score   = sum(n["impact_score"] * n["weight"] for n in scored_news)
        total_weight  = sum(n["weight"] for n in scored_news)
        avg_sentiment = total_score / total_weight if total_weight > 0 else 0

        # Classify overall sentiment
        overall = self._classify_overall(avg_sentiment)

        # Top movers
        top_positive = [n for n in scored_news if n["impact_score"] > 0.5][:3]
        top_negative = [n for n in scored_news if n["impact_score"] < -0.5][:3]

        # Market impact prediction
        impact = self._predict_market_impact(avg_sentiment, scored_news)

        return {
            "overall_sentiment":   overall,
            "sentiment_score":     round(avg_sentiment, 3),
            "total_articles":      len(news_items),
            "top_positive_news":   top_positive,
            "top_negative_news":   top_negative,
            "market_impact":       impact,
            "timestamp":           datetime.now().isoformat(),
            "key_themes":          self._extract_key_themes(scored_news),
            "event_alerts":        self._detect_event_alerts(scored_news),
        }

    def _fetch_all_news(self) -> list:
        """Fetch from all RSS sources."""
        # Use cache if fresh
        if (self.last_fetch_time and
            (datetime.now() - self.last_fetch_time).seconds < self.cache_duration * 60 and
            self.news_cache):
            return self.news_cache

        all_news = []
        for source_key, source in NEWS_SOURCES.items():
            items = self._fetch_rss(source["rss"], source["name"], source["weight"])
            all_news.extend(items)

        # Filter to last 6 hours
        cutoff = datetime.now() - timedelta(hours=6)
        # (RSS entries often don't have timestamps, so we keep all for now)

        self.news_cache      = all_news[:50]  # keep top 50
        self.last_fetch_time = datetime.now()
        logger.info(f"Fetched {len(all_news)} news items")
        return self.news_cache

    def _fetch_rss(self, url: str, source_name: str, weight: float) -> list:
        """Fetch and parse RSS feed."""
        try:
            feed    = feedparser.parse(url)
            items   = []
            for entry in feed.entries[:10]:  # top 10 per source
                headline = entry.get("title", "")
                summary  = entry.get("summary", "")
                link     = entry.get("link", "")
                if headline:
                    items.append({
                        "headline": headline,
                        "summary":  summary,
                        "source":   source_name,
                        "weight":   weight,
                        "url":      link,
                    })
            return items
        except Exception as e:
            logger.debug(f"RSS fetch failed for {source_name}: {e}")
            return []

    def _score_news_item(self, item: dict) -> dict:
        """Score a single news item for NIFTY impact."""
        text = f"{item['headline']} {item['summary']}".lower()

        # VADER sentiment
        if HAS_VADER:
            scores = VADER.polarity_scores(item["headline"])
            vader_score = scores["compound"]  # -1 to +1
        else:
            vader_score = self._basic_sentiment(text)

        # Keyword boost
        keyword_boost = 0
        matched_keywords = []

        for kw in NIFTY_KEYWORDS["high_positive"]:
            if kw in text:
                keyword_boost += 0.4
                matched_keywords.append(f"+{kw}")

        for kw in NIFTY_KEYWORDS["moderate_positive"]:
            if kw in text:
                keyword_boost += 0.2
                matched_keywords.append(f"+{kw}")

        for kw in NIFTY_KEYWORDS["high_negative"]:
            if kw in text:
                keyword_boost -= 0.4
                matched_keywords.append(f"-{kw}")

        for kw in NIFTY_KEYWORDS["moderate_negative"]:
            if kw in text:
                keyword_boost -= 0.2
                matched_keywords.append(f"-{kw}")

        # Is event-driven?
        is_event = any(kw in text for kw in NIFTY_KEYWORDS["event_driven"])

        # Final impact score (combine VADER + keyword)
        impact_score = (vader_score * 0.5 + keyword_boost * 0.5)
        impact_score = max(-1.0, min(1.0, impact_score))

        # Classify
        impact_class = classify_news_impact(item["headline"])

        return {
            **item,
            "impact_score":     round(impact_score, 3),
            "vader_score":      round(vader_score, 3),
            "keyword_matches":  matched_keywords,
            "is_event_driven":  is_event,
            "impact_class":     impact_class["sentiment"],
            "sentiment_label":  "POSITIVE" if impact_score > 0.1 else ("NEGATIVE" if impact_score < -0.1 else "NEUTRAL"),
        }

    def _basic_sentiment(self, text: str) -> float:
        """Fallback sentiment without VADER."""
        positive = sum(1 for kw in NIFTY_KEYWORDS["high_positive"] + NIFTY_KEYWORDS["moderate_positive"] if kw in text)
        negative = sum(1 for kw in NIFTY_KEYWORDS["high_negative"] + NIFTY_KEYWORDS["moderate_negative"] if kw in text)
        total = positive + negative
        if total == 0: return 0.0
        return (positive - negative) / total

    def _classify_overall(self, score: float) -> str:
        if score >  0.5: return "VERY_POSITIVE"
        if score >  0.2: return "POSITIVE"
        if score > -0.2: return "NEUTRAL"
        if score > -0.5: return "NEGATIVE"
        return "VERY_NEGATIVE"

    def _predict_market_impact(self, avg_score: float, news: list) -> dict:
        """Predict likely NIFTY move from news sentiment."""
        event_news = [n for n in news if n.get("is_event_driven")]
        has_major_event = len(event_news) > 0

        if avg_score > 0.5:
            direction = "UP"; magnitude = "+1.0% to +2.5%"
        elif avg_score > 0.2:
            direction = "UP"; magnitude = "+0.3% to +1.0%"
        elif avg_score < -0.5:
            direction = "DOWN"; magnitude = "-1.0% to -2.5%"
        elif avg_score < -0.2:
            direction = "DOWN"; magnitude = "-0.3% to -1.0%"
        else:
            direction = "NEUTRAL"; magnitude = "±0.2%"

        return {
            "direction": direction,
            "magnitude": magnitude,
            "has_major_event": has_major_event,
            "high_impact_warning": abs(avg_score) > 0.4,
            "recommendation": (
                "BUY calls" if avg_score > 0.3 else
                "BUY puts" if avg_score < -0.3 else
                "Stay neutral — wait for price confirmation"
            ),
        }

    def _extract_key_themes(self, news: list) -> list:
        """Extract dominant themes from all news."""
        theme_counts = {}
        all_text = " ".join(n["headline"].lower() for n in news)
        themes = {
            "RBI/Rates":       ["rbi", "interest rate", "repo rate", "monetary policy"],
            "FII Activity":    ["fii", "foreign investor", "fpi", "dii"],
            "Global Markets":  ["dow", "nasdaq", "fed", "global", "us market", "asia"],
            "Corporate":       ["results", "earnings", "profit", "revenue", "quarterly"],
            "Macro":           ["gdp", "inflation", "cpi", "iip", "trade deficit"],
            "Commodity":       ["crude", "oil", "gold", "metal", "commodity"],
            "Banking/Finance": ["bank", "nbfc", "credit", "npa", "loan"],
        }
        active_themes = []
        for theme, keywords in themes.items():
            if any(kw in all_text for kw in keywords):
                active_themes.append(theme)
        return active_themes

    def _detect_event_alerts(self, news: list) -> list:
        """Alert on major upcoming or current market events."""
        alerts = []
        event_indicators = {
            "RBI Policy Decision": ["rbi policy", "monetary policy committee", "mpc"],
            "US Fed Meeting": ["fomc", "fed meeting", "powell"],
            "Budget": ["union budget", "finance minister", "budget 2024", "budget 2025"],
            "Expiry": ["expiry", "derivatives", "f&o expiry"],
            "Quarterly Results": ["q1 results", "q2 results", "q3 results", "q4 results"],
        }
        all_text = " ".join(n["headline"].lower() for n in news)
        for event, keywords in event_indicators.items():
            if any(kw in all_text for kw in keywords):
                alerts.append(event)
        return alerts

    def _empty_sentiment(self) -> dict:
        return {
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0,
            "total_articles": 0,
            "top_positive_news": [],
            "top_negative_news": [],
            "market_impact": {"direction": "NEUTRAL", "magnitude": "±0.2%", "has_major_event": False,
                               "high_impact_warning": False, "recommendation": "Wait for data"},
            "timestamp": datetime.now().isoformat(),
            "key_themes": [],
            "event_alerts": [],
        }

    def get_sentiment_for_ai_prompt(self) -> str:
        """Format sentiment for injection into AI prompts."""
        s = self.get_market_sentiment()
        lines = [
            f"NEWS SENTIMENT ANALYSIS:",
            f"Overall: {s['overall_sentiment']} (score={s['sentiment_score']:.2f})",
            f"Articles analyzed: {s['total_articles']}",
            f"Key themes: {', '.join(s['key_themes']) if s['key_themes'] else 'None detected'}",
            f"Event alerts: {', '.join(s['event_alerts']) if s['event_alerts'] else 'None'}",
            f"Market impact: {s['market_impact']['direction']} ({s['market_impact']['magnitude']})",
            f"Recommendation: {s['market_impact']['recommendation']}",
        ]
        if s["top_positive_news"]:
            lines.append("Top positive: " + s["top_positive_news"][0]["headline"])
        if s["top_negative_news"]:
            lines.append("Top negative: " + s["top_negative_news"][0]["headline"])
        return "\n".join(lines)
