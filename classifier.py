"""
CivicFix AI - Classification & Priority Engine
Groq API integration with strict validation and deterministic rule-based fallback.
"""

import json
import logging
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT_SECONDS,
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
)

logger = logging.getLogger("civicfix.classifier")


def classify_rule_based(title: str, description: str) -> dict:
    """
    Deterministic rule-based classification and priority assignment.
    Guaranteed fallback when Groq API is unavailable, timed out, or unconfigured.
    """
    text = f"{title} {description}".lower()

    # Keyword dictionaries for categories
    category_keywords = {
        "Roads & potholes": [
            "pothole", "crater", "road", "asphalt", "tar", "divider", "footpath",
            "speed breaker", "pavement", "street hole", "traffic bump", "flyover",
        ],
        "Garbage & sanitation": [
            "garbage", "trash", "waste", "dump", "dustbin", "litter", "smell",
            "stench", "dead animal", "filth", "cleaning", "rubbish", "debris",
            "sweeper", "safai",
        ],
        "Streetlights": [
            "streetlight", "street light", "lamp", "dark", "bulb", "lighting",
            "pole", "electric pole", "blackout", "lantern", "lights off",
        ],
        "Water supply & leakage": [
            "water", "pipe", "pipeline", "leak", "leakage", "tap", "drinking water",
            "supply", "jal", "tanker", "burst pipe", "water pressure",
        ],
        "Drainage & sewage": [
            "drain", "drainage", "sewage", "gutter", "overflow", "manhole", "clog",
            "sewer", "dirty water", "waterlogging", "nalah", "backflow", "sludge",
        ],
        "Public safety / hazard": [
            "danger", "hazard", "fire", "electric shock", "exposed wire", "live wire",
            "open wire", "collapse", "falling tree", "accident", "emergency", "gas leak",
            "electrocution",
        ],
        "Parks & public spaces": [
            "park", "garden", "bench", "playground", "swing", "grass", "tree trimming",
            "jogging track", "public lawn", "monument", "horticulture",
        ],
    }

    # Score categories
    best_category = "Other / needs review"
    max_score = 0
    for category, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > max_score:
            max_score = score
            best_category = category

    # High priority indicators
    high_priority_keywords = [
        "danger", "hazard", "fatal", "emergency", "fire", "shock", "live wire",
        "open manhole", "burst", "bursting", "arterial", "main road", "hospital",
        "school", "collapse", "flooding", "electrocution", "severe", "accident",
        "pitch dark", "dead animal",
    ]

    # Medium priority indicators
    medium_priority_keywords = [
        "overflow", "stench", "market", "blocked", "leak", "uncollected",
        "delay", "commuters", "commercial", "pedestrian", "inconvenience",
        "smell", "pothole", "dark", "no water",
    ]

    has_high = any(kw in text for kw in high_priority_keywords) or (best_category == "Public safety / hazard")
    has_med = any(kw in text for kw in medium_priority_keywords)

    if has_high:
        priority = "High"
        reason = "Immediate public safety peril or severe infrastructure disruption requiring rapid emergency intervention."
    elif has_med or best_category in ["Garbage & sanitation", "Water supply & leakage", "Drainage & sewage", "Streetlights"]:
        priority = "Medium"
        reason = "Significant civic inconvenience impacting neighborhood mobility, hygiene, or basic public utilities."
    else:
        priority = "Low"
        reason = "Routine municipal maintenance scheduled within standard operational workflow."

    return {
        "category": best_category,
        "priority": priority,
        "reason": reason,
        "source": "rules_fallback",
    }


def classify_with_groq(title: str, description: str) -> dict:
    """
    Calls Groq API to obtain high-accuracy classification and transparent priority reasoning.
    Validates output strictly. Returns None on any failure to enable graceful fallback.
    """
    if not GROQ_API_KEY:
        logger.info("GROQ_API_KEY is not set. Using rule-based classification.")
        return None

    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT_SECONDS)

        categories_str = "\n".join(f"- {cat}" for cat in ALLOWED_CATEGORIES)
        system_prompt = (
            "You are an expert civic infrastructure classifier for the Lucknow Municipal Corporation (LMC).\n"
            "Analyze the citizen complaint and classify it into exactly one of these allowed categories:\n"
            f"{categories_str}\n\n"
            "Assign an appropriate priority level:\n"
            "- 'High': Life-safety hazards, open live wires, open manholes, major water main bursts, deep potholes on high-speed roads, fire risks.\n"
            "- 'Medium': Overflowing community garbage, dark residential streets, regular pipe leaks, blocked storm drains, traffic impediments.\n"
            "- 'Low': Cosmetic road markings, routine park maintenance, broken benches, non-urgent municipal upkeep.\n\n"
            "Provide a transparent, concise 1-sentence justification explaining to the citizen why this priority was assigned.\n"
            "Respond ONLY with a valid JSON object with exact keys: 'category', 'priority', 'reason'. No additional text or markdown formatting."
        )

        user_content = f"Title: {title.strip()}\nDescription: {description.strip()}"

        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        response_text = completion.choices[0].message.content.strip()
        data = json.loads(response_text)

        category = data.get("category", "").strip()
        priority = data.get("priority", "").capitalize().strip()
        reason = data.get("reason", "").strip()

        # Strict validation
        if category not in ALLOWED_CATEGORIES:
            logger.warning("Groq returned unallowed category: %s. Falling back to rules.", category)
            return None

        if priority not in ALLOWED_PRIORITIES:
            logger.warning("Groq returned unallowed priority: %s. Falling back to rules.", priority)
            return None

        if not reason:
            reason = f"Prioritized as {priority} based on civic impact and municipal service standards."

        return {
            "category": category,
            "priority": priority,
            "reason": reason,
            "source": "groq_api",
        }

    except Exception as e:
        logger.warning("Groq API classification failed or timed out: %s. Engaging rule-based fallback.", e)
        return None


def classify_complaint(title: str, description: str) -> dict:
    """
    Main entry point for classification.
    Tries Groq API first; seamlessly falls back to rule-based engine on failure or timeout.
    """
    groq_result = classify_with_groq(title, description)
    if groq_result:
        return groq_result
    return classify_rule_based(title, description)

