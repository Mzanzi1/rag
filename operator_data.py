# C:\AI Projects\rag2\operator_data.py
import re
from qdrant_client import models
from typing import List, Set, Tuple

# ============================================================================
# 🌍 1. DOMAIN DATA
# ============================================================================

TECH_KEYWORDS = [
    "xcap", "5g", "volte", "vowifi", "nr", "nsa", "binary", "plm", "s25", "s936b",
    "firmware", "oneui", "z8", "foldable", "iot", "carrier aggregation", "mdt",
    "dual stack", "ipv4/ipv6", "ipv4", "ipv6", "vilte", "sa", "dss", "mimo",
    "beamforming", "ca", "vonr", "eps fb", "ims", "smsoip", "handover",
    "throughput", "latency", "b0", "q0", "sm-", "imei", "csc", "modem", "ap",
    "cp", "rrc", "nas", "l1", "l2", "l3", "fit", "field test", "lab test",
    "log", "dump", "wireshark", "pcap", "mr", "regression", "blocker",
    "silent logging", "procedure", "dumpstate", "ramdump"
]

country_data = {
    "UAE": {"subsidiaries": ["SGE"], "operators": ["Etisalat", "Du", "Virgin Mobile"]},
    "Kuwait": {"subsidiaries": ["SGE"], "operators": ["Zain", "Ooredoo", "STC", "Virgin Mobile"]},
    "Oman": {"subsidiaries": ["SGE"], "operators": ["Omantel", "Ooredoo", "Vodafone"]},
    "Bahrain": {"subsidiaries": ["SGE"], "operators": ["Batelco", "Zain", "STC"]},
    "Qatar": {"subsidiaries": ["SGE"], "operators": ["Vodafone", "Ooredoo"]},
    "Yemen": {"subsidiaries": ["SGE"], "operators": ["You Telecom", "Sabafon", "Yemen Mobile", "Y-Telecom"]},
    "Saudi Arabia": {"subsidiaries": ["SESAR"], "operators": ["STC", "Mobily", "Zain", "Salam", "Virgin Mobile", "Redbull Mobile", "Lebara"], "aliases": ["KSA", "Saudi"]},
    "Turkey": {"subsidiaries": ["SETK"], "operators": ["Vodafone", "Turkcell", "TurkTelekom"], "aliases": ["Turkiye", "Türkiye"]},
    "Jordan": {"subsidiaries": ["SELV"], "operators": ["Zain", "Orange", "Umniah"]},
    "Lebanon": {"subsidiaries": ["SELV"], "operators": ["Touch", "Alfa"]},
    "Iraq": {"subsidiaries": ["SELV"], "operators": ["Zain", "Asiacell", "Korek"]},
    "Israel": {"subsidiaries": ["SEIL"], "operators": ["Cellcom", "Partner", "Pelephone", "Hot Mobile", "Annatel", "Webbing", "Xfone/018", "019", "Wecom/We4G", "Free Telecom"]},
    "Palestine": {"subsidiaries": ["SEIL"], "operators": ["Jawwal", "Ooredoo"]},
    "Egypt": {"subsidiaries": ["SEEG"], "operators": ["Vodafone", "Orange", "Etisalat", "We"]},
    "Morocco": {"subsidiaries": ["SEMAG"], "operators": ["Maroc Telecom", "Orange", "Inwi", "Win"]},
    "Tunisia": {"subsidiaries": ["SEMAG"], "operators": ["Tunisia Telecom", "Orange", "Ooredoo"]},
    "Algeria": {"subsidiaries": ["SEMAG"], "operators": ["Djezzy", "Ooredoo", "Mobilis"]},
    "Libya": {"subsidiaries": ["SEMAG"], "operators": ["Al Madar", "Libyana", "LTT Libya Telecom & Technology"]},
    "Pakistan": {"subsidiaries": ["SEPAK"], "operators": ["Jazz", "Telenor", "Ufone", "Zong", "SCO Mobile", "Onic"]},
    "Afghanistan": {"subsidiaries": ["SEPAK"], "operators": ["AWCC", "Roshan", "ATOMA", "Etisalat", "Salaam"]},
    "Iran": {"subsidiaries": ["Iran"], "operators": ["MCI Hamrahe Aval", "MTN Irancell", "Rightel", "Samantel", "Shatel"]},
    "Syria": {"subsidiaries": ["Syria"], "operators": ["Syriatel", "MTN"]}
}

def get_all_operators() -> List[str]:
    operators: Set[str] = set()
    for data in country_data.values():
        operators.update(data.get("operators", []))
    return sorted(list(operators))

# ============================================================================
# 🧠 2. WATERFALL LOGIC
# ============================================================================

def get_query_context(query: str, base_threshold: float, expanded_operators=None):
    query_lower = query.lower().strip()
    active_threshold = 0.40
    labels = []
    target_operators = set()
    hierarchy_found = False

    # 1. & 2. Subsidiaries/Countries
    for country, data in country_data.items():
        search_terms = [country.lower()] + [a.lower() for a in data.get("aliases", [])]
        subsidiaries = [s.lower() for s in data.get("subsidiaries", [])]
        if any(term in query_lower for term in search_terms) or any(sub in query_lower for sub in subsidiaries):
            if country not in labels: labels.append(country)
            target_operators.update(data["operators"])
            hierarchy_found = True

    # 3. Operators
    for op in get_all_operators():
        if re.search(r'\b' + re.escape(op.lower()) + r'\b', query_lower):
            if op not in labels: labels.append(op)
            target_operators = {op}
            hierarchy_found = True
            break

    if expanded_operators:
        target_operators.update(expanded_operators)
        hierarchy_found = True
        if "DGraph" not in labels: labels.insert(0, "DGraph")

    must_conditions = []
    should_conditions = []

    if hierarchy_found and target_operators:
        h_filters = []
        for op in target_operators:
            h_filters.append(models.FieldCondition(key="operators", match=models.MatchValue(value=op)))
            h_filters.append(models.FieldCondition(key="operator", match=models.MatchValue(value=op)))
        must_conditions.append(models.Filter(should=h_filters))

    # 4. Tech Keywords (MatchText handles partial/text matching)
    for tech in TECH_KEYWORDS:
        if re.search(r'\b' + re.escape(tech.lower()) + r'\b', query_lower):
            if tech.upper() not in labels: labels.append(tech.upper())
            should_conditions.append(models.FieldCondition(key="subject", match=models.MatchText(text=tech)))
            should_conditions.append(models.FieldCondition(key="body", match=models.MatchText(text=tech)))

    final_filter = models.Filter(
        must=must_conditions if must_conditions else None,
        should=should_conditions if should_conditions else None
    )
    return final_filter, " > ".join(dict.fromkeys(labels)) if labels else "General", active_threshold
