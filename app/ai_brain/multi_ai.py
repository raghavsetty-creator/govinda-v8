"""
NIFTY AI Trading System — Multi-AI Consensus Brain
====================================================
Orchestrates multiple AI models for consensus-based trading decisions:
  - Claude (Anthropic) — Reasoning + Pattern Analysis
  - GPT-4 (OpenAI)    — Market context + Risk assessment
  - Gemini Pro (Google) — News sentiment + Alternative view
  
Each AI receives the full market context and gives its verdict.
A consensus vote + confidence weighting produces the final signal.

This is the "Council of AI advisors" model — no single AI dominates.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge.market_knowledge import get_full_context_for_ai, CANDLESTICK_PATTERNS, CHART_PATTERNS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# MASTER PROMPT — Sent to ALL AI models
# ═══════════════════════════════════════════════════════════════════════════

MASTER_TRADING_PROMPT = """You are an expert NIFTY 50 options trading analyst with 20+ years experience.
You understand candlestick patterns, chart patterns, multi-timeframe analysis, Open Interest dynamics, 
trader psychology, and Indian market structure deeply.

Analyze the following market data and provide your trading recommendation.

{market_context}

{mtf_analysis}

{news_sentiment}

{patterns_detected}

{oi_data}

Based on ALL the above, provide your analysis in the following JSON format ONLY:
{{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0.0 to 1.0,
    "reasoning": "2-3 sentence explanation",
    "key_risk": "Main risk to this trade",
    "options_suggestion": "e.g. Buy CE at X strike / Buy PE at Y strike",
    "target": "Expected move target",
    "stop_loss": "Stop loss level",
    "time_horizon": "Intraday/Expiry/Next session",
    "psychology_note": "Any behavioral bias to watch for"
}}

Be concise, specific, and actionable. No disclaimers."""


class AIBrain:
    """
    Multi-AI consensus trading brain.
    Aggregates signals from Claude, GPT-4, and Gemini.
    """

    def __init__(self):
        self.claude_client  = self._init_claude()
        self.openai_client  = self._init_openai()
        self.gemini_client  = self._init_gemini()
        self.response_cache = {}

    # ─────────────────────────────────────────
    # INITIALIZATION
    # ─────────────────────────────────────────

    def _init_claude(self):
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if api_key:
                client = anthropic.Anthropic(api_key=api_key)
                logger.info("✅ Claude (Anthropic) — Connected")
                return client
        except ImportError:
            pass
        logger.info("⚠️  Claude — Not configured (set ANTHROPIC_API_KEY)")
        return None

    def _init_openai(self):
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                client = openai.OpenAI(api_key=api_key)
                logger.info("✅ GPT-4 (OpenAI) — Connected")
                return client
        except ImportError:
            pass
        logger.info("⚠️  GPT-4 — Not configured (set OPENAI_API_KEY)")
        return None

    def _init_gemini(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.info("⚠️  Gemini — Not configured (set GEMINI_API_KEY)")
            return None
        try:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                logger.info("✅ Gemini (google.genai) — Connected")
                return {"client": client, "version": "new"}
            except ImportError:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-pro")
                logger.info("✅ Gemini Pro (legacy) — Connected")
                return {"client": model, "version": "legacy"}
        except Exception as e:
            logger.info(f"⚠️  Gemini init failed: {e}")
            return None

    # ─────────────────────────────────────────
    # CONSENSUS SIGNAL GENERATION
    # ─────────────────────────────────────────

    def get_consensus_signal(
        self,
        ml_signal: dict,
        mtf_report: dict,
        news_sentiment: dict,
        patterns: list,
        oi_data: dict = None,
    ) -> dict:
        """
        Get consensus signal from all available AI models.
        Falls back gracefully if models unavailable.
        """
        # Build the unified market context
        prompt = self._build_master_prompt(ml_signal, mtf_report, news_sentiment, patterns, oi_data)

        # Query each AI
        ai_responses = {}

        if self.claude_client:
            ai_responses["claude"] = self._query_claude(prompt)
        if self.openai_client:
            ai_responses["gpt4"] = self._query_openai(prompt)
        if self.gemini_client:
            ai_responses["gemini"] = self._query_gemini(prompt)

        # If no AI available, use ML model only
        if not ai_responses:
            logger.info("No AI models configured — using ML model signal only")
            return self._ml_only_response(ml_signal)

        # Parse and validate AI responses
        parsed = {}
        for ai_name, response in ai_responses.items():
            parsed_resp = self._parse_ai_response(response, ai_name)
            if parsed_resp:
                parsed[ai_name] = parsed_resp

        if not parsed:
            return self._ml_only_response(ml_signal)

        # Build consensus
        return self._build_consensus(parsed, ml_signal)

    # ─────────────────────────────────────────
    # PROMPT BUILDER
    # ─────────────────────────────────────────

    def _build_master_prompt(
        self,
        ml_signal: dict,
        mtf_report: dict,
        news_sentiment: dict,
        patterns: list,
        oi_data: dict,
    ) -> str:
        """Build the comprehensive prompt sent to all AIs."""

        market_context = f"""
MARKET DATA (NIFTY 50 — 5-Minute Chart):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Price:    ₹{ml_signal.get('price', 0):,.0f}
ML Signal:        {ml_signal.get('signal', 'HOLD')} ({ml_signal.get('confidence', 0):.1%} confidence)
Market Regime:    {ml_signal.get('regime', 'UNKNOWN')}
ADX:              {ml_signal.get('adx', 0):.1f}
RSI:              {ml_signal.get('rsi', 0):.1f}
BUY Probability:  {ml_signal.get('buy_prob', 0):.1%}
SELL Probability: {ml_signal.get('sell_prob', 0):.1%}

ML Reasoning:
{chr(10).join(f'• {r}' for r in ml_signal.get('reasoning', []))}
"""

        mtf_context = f"""
MULTI-TIMEFRAME ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━
Overall Bias:  {mtf_report.get('overall_bias', 'N/A')}
Confluence:    {mtf_report.get('confluence', 0)}/10
Bullish TFs:   {', '.join(mtf_report.get('bullish_tfs', ['None']))}
Bearish TFs:   {', '.join(mtf_report.get('bearish_tfs', ['None']))}
"""
        for tf, sig in mtf_report.get("timeframes", {}).items():
            mtf_context += f"  {sig['label']:8s}: {sig['bias']:12s} ADX={sig['adx']:4.1f} RSI={sig['rsi']:4.1f}\n"

        news_context = f"""
NEWS SENTIMENT:
━━━━━━━━━━━━━━
Overall:    {news_sentiment.get('overall_sentiment', 'NEUTRAL')}
Score:      {news_sentiment.get('sentiment_score', 0):.2f} (range -1 to +1)
Themes:     {', '.join(news_sentiment.get('key_themes', ['None']))}
Alerts:     {', '.join(news_sentiment.get('event_alerts', ['None']))}
Impact:     {news_sentiment.get('market_impact', {}).get('direction', 'NEUTRAL')} {news_sentiment.get('market_impact', {}).get('magnitude', '')}
"""
        if news_sentiment.get("top_positive_news"):
            news_context += f"Top Positive: {news_sentiment['top_positive_news'][0].get('headline', '')}\n"
        if news_sentiment.get("top_negative_news"):
            news_context += f"Top Negative: {news_sentiment['top_negative_news'][0].get('headline', '')}\n"

        patterns_context = "DETECTED PATTERNS:\n━━━━━━━━━━━━━━━━━━\n"
        if patterns:
            for p in patterns[:5]:
                patterns_context += f"• {p['pattern'].replace('_', ' ').title()}: {p['direction']} (reliability={p['reliability']:.0%})\n"
                if p.get("psychology"):
                    patterns_context += f"  Psychology: {p['psychology']}\n"
        else:
            patterns_context += "No significant patterns detected\n"

        oi_context = "OI DATA:\n━━━━━━━━\n"
        if oi_data:
            oi_context += f"PCR: {oi_data.get('pcr', 'N/A')}\n"
            oi_context += f"Max Pain: {oi_data.get('max_pain', 'N/A')}\n"
            oi_context += f"Call Max OI Strike: {oi_data.get('call_max_oi_strike', 'N/A')} (resistance)\n"
            oi_context += f"Put Max OI Strike: {oi_data.get('put_max_oi_strike', 'N/A')} (support)\n"
            oi_context += f"OI Interpretation: {oi_data.get('interpretation', 'N/A')}\n"
        else:
            oi_context += "OI data not available — factor in OI from option chain manually\n"

        return MASTER_TRADING_PROMPT.format(
            market_context=market_context,
            mtf_analysis=mtf_context,
            news_sentiment=news_context,
            patterns_detected=patterns_context,
            oi_data=oi_context,
        )

    # ─────────────────────────────────────────
    # QUERY INDIVIDUAL AIs
    # ─────────────────────────────────────────

    def _query_claude(self, prompt: str) -> str:
        """Query Anthropic Claude."""
        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            response = message.content[0].text
            logger.info("Claude responded")
            return response
        except Exception as e:
            logger.warning(f"Claude query failed: {e}")
            return ""

    def _query_openai(self, prompt: str) -> str:
        """Query OpenAI GPT-4."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert NIFTY options trader. Respond only in JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = response.choices[0].message.content
            logger.info("GPT-4 responded")
            return result
        except Exception as e:
            logger.warning(f"GPT-4 query failed: {e}")
            return ""

    def _query_gemini(self, prompt: str) -> str:
        """Query Google Gemini."""
        try:
            version = self.gemini_client.get("version", "legacy")
            client  = self.gemini_client["client"]
            full_prompt = prompt + "\n\nRespond in JSON format only."
            if version == "new":
                response = client.models.generate_content(
                    model="gemini-2.0-flash", contents=full_prompt)
            else:
                response = client.generate_content(
                    full_prompt, generation_config={"temperature": 0.3, "max_output_tokens": 500})
            logger.info("Gemini responded")
            return response.text
        except Exception as e:
            logger.warning(f"Gemini query failed: {e}")
            return ""

    # ─────────────────────────────────────────
    # CONSENSUS BUILDING
    # ─────────────────────────────────────────

    def _parse_ai_response(self, response: str, ai_name: str) -> Optional[dict]:
        """Parse and validate AI JSON response."""
        if not response:
            return None
        try:
            # Extract JSON from response
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)

            # Validate required fields
            if "signal" not in data or data["signal"] not in ["BUY", "SELL", "HOLD"]:
                return None

            data["ai_source"] = ai_name
            data["confidence"] = float(data.get("confidence", 0.5))
            return data

        except Exception as e:
            logger.debug(f"Failed to parse {ai_name} response: {e}")
            return None

    def _build_consensus(self, ai_responses: dict, ml_signal: dict) -> dict:
        """
        Build final consensus from all AI + ML signals.
        Voting system with confidence weighting.
        """
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        confidence_total = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

        # AI votes (weight = 1.5 each)
        for ai_name, resp in ai_responses.items():
            signal = resp["signal"]
            conf   = resp["confidence"]
            votes[signal] += 1.5
            confidence_total[signal] += conf * 1.5

        # ML model vote (weight = 1.0)
        ml_sig = ml_signal.get("signal", "HOLD")
        ml_conf = ml_signal.get("confidence", 0.5)
        votes[ml_sig] += 1.0
        confidence_total[ml_sig] += ml_conf

        # Consensus signal = highest vote
        consensus_signal = max(votes, key=votes.get)
        total_votes = sum(votes.values())
        vote_pct = votes[consensus_signal] / total_votes if total_votes > 0 else 0

        # Consensus confidence = weighted average
        if votes[consensus_signal] > 0:
            consensus_confidence = confidence_total[consensus_signal] / votes[consensus_signal]
        else:
            consensus_confidence = 0.5

        # Agreement level
        if vote_pct >= 0.9:
            agreement = "UNANIMOUS"
        elif vote_pct >= 0.7:
            agreement = "STRONG"
        elif vote_pct >= 0.5:
            agreement = "MAJORITY"
        else:
            agreement = "SPLIT"

        # Collect all reasoning
        all_reasoning = [f"ML: {r}" for r in ml_signal.get("reasoning", [])[:2]]
        for ai_name, resp in ai_responses.items():
            if resp.get("reasoning"):
                all_reasoning.append(f"{ai_name.upper()}: {resp['reasoning']}")

        # Primary recommendation (highest confidence AI if available)
        primary_ai = max(ai_responses.items(), key=lambda x: x[1]["confidence"]) if ai_responses else None

        return {
            "signal":               consensus_signal,
            "confidence":           round(consensus_confidence, 4),
            "agreement":            agreement,
            "vote_breakdown":       votes,
            "vote_pct":             round(vote_pct, 3),
            "ai_count":             len(ai_responses),
            "timestamp":            datetime.now().isoformat(),
            "price":                ml_signal.get("price", 0),
            "adx":                  ml_signal.get("adx", 0),
            "rsi":                  ml_signal.get("rsi", 0),
            "regime":               ml_signal.get("regime", "UNKNOWN"),
            "all_reasoning":        all_reasoning,
            "options_suggestion":   primary_ai[1].get("options_suggestion", "N/A") if primary_ai else "N/A",
            "target":               primary_ai[1].get("target", "N/A") if primary_ai else "N/A",
            "stop_loss":            primary_ai[1].get("stop_loss", "N/A") if primary_ai else "N/A",
            "key_risk":             primary_ai[1].get("key_risk", "N/A") if primary_ai else "N/A",
            "psychology_note":      primary_ai[1].get("psychology_note", "N/A") if primary_ai else "N/A",
            "individual_responses": {k: v for k, v in ai_responses.items()},
            "action_recommended":   agreement in ["UNANIMOUS", "STRONG"] and consensus_signal != "HOLD",
            "emoji":                "🟢" if consensus_signal == "BUY" else ("🔴" if consensus_signal == "SELL" else "⚪"),
        }

    def _ml_only_response(self, ml_signal: dict) -> dict:
        """Fallback when no AI models available."""
        return {
            **ml_signal,
            "agreement": "ML_ONLY",
            "vote_breakdown": {ml_signal.get("signal", "HOLD"): 1},
            "ai_count": 0,
            "all_reasoning": ml_signal.get("reasoning", []),
            "options_suggestion": "N/A",
            "target": "N/A",
            "stop_loss": "N/A",
            "key_risk": "N/A — add API keys for AI analysis",
            "psychology_note": "N/A",
            "individual_responses": {},
        }

    def get_status(self) -> dict:
        """Return which AI models are connected."""
        return {
            "claude":  self.claude_client  is not None,
            "gpt4":    self.openai_client  is not None,
            "gemini":  self.gemini_client  is not None,
            "total_active": sum([
                self.claude_client  is not None,
                self.openai_client  is not None,
                self.gemini_client  is not None,
            ])
        }
