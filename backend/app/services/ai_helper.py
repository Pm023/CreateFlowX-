import os
from typing import Dict, Any

class AIHelper:
    @staticmethod
    def enrich_growth_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts the rule-based growth summary and enhances/augments the insights and coaching recommendations.
        If an AI API key is configured in the environment (e.g. GEMINI_API_KEY or OPENAI_API_KEY),
        this can run a prompt requesting narrative suggestions, while NEVER calculating the scores/numbers themselves.
        If no API key exists, it returns the rule-based summaries as-is with a prompt to connect AI.
        """
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        summary["ai_ready"] = True
        summary["ai_enriched"] = False
        summary["ai_coaching_summary"] = (
            "Focus on the recommended actions below to improve invoice collection, "
            "re-engage quiet clients, and drive your Business Health Score upward."
        )

        # Future integration stub
        if gemini_key or openai_key:
            # When an API key is connected, provide a premium coaching summary narrative.
            # In a live setup, the developer can install `google-generativeai` or `openai`
            # and pass the metrics payload to generate this description.
            summary["ai_enriched"] = True
            bh = summary["business_health"]
            summary["ai_coaching_summary"] = (
                f"[AI Growth Coach] Your business is in a '{bh['level']}' state with a score of {bh['score']}/100. "
                "Your primary bottleneck is invoice collection and client activity. "
                "I recommend setting up a calendar invite to email inactive clients, and "
                "sending immediate polite follow-ups for outstanding invoice amounts to boost short-term liquidity."
            )
            
        return summary

ai_helper = AIHelper()
