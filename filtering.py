# C:\AI Projects\rag2\filtering.py
import re
from typing import Dict, List, Any
from qdrant_client.http import models

# CRITICAL FIX: Match the variable name in your operator_data.py
try:
    from operator_data import country_data as COUNTRY_DATA
except ImportError:
    print("⚠️ Warning: Could not find country_data in operator_data.py")
    COUNTRY_DATA = {}


def parse_filters(query: str) -> Dict[str, List[str]]:
    # Normalize query for matching
    q_clean = query.lower()
    found_ops = set()
    found_countries = set()

    for country_name, data in COUNTRY_DATA.items():
        c_key = country_name.strip()

        # 1. Match Country (e.g., "Syria")
        if c_key.lower() in q_clean:
            found_countries.add(c_key)
            # Auto-add operators for that country
            for op in data.get("operators", []):
                found_ops.add(op.strip())

        # 2. Match Specific Operators (e.g., "MTN")
        for op in data.get("operators", []):
            o_key = op.strip()
            if o_key.lower() in q_clean:
                found_ops.add(o_key)
                found_countries.add(c_key)

    return {
        "operators": list(found_ops),
        "countries": list(found_countries)
    }


def build_qdrant_filter(filters: Dict[str, List[str]]) -> Any:
    """Uses MatchAny to handle the List format confirmed by your inspection."""
    should_conditions = []

    if filters.get("operators"):
        should_conditions.append(
            models.FieldCondition(
                key="operators",
                match=models.MatchAny(any=filters["operators"])
            )
        )

    if filters.get("countries"):
        should_conditions.append(
            models.FieldCondition(
                key="countries",
                match=models.MatchAny(any=filters["countries"])
            )
        )

    return models.Filter(should=should_conditions) if should_conditions else None


