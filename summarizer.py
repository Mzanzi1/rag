# C:\AI Projects\rag2\summarizer.py

def summarize(agent_results, query):
    """
    Synthesizes agent findings into a structured final report.
    """
    report_blocks = []
    total_confidence = 0.0
    valid_agents = 0

    for result in agent_results:
        name = result.get("agent", "Agent")

        # 1. Handle Technical Errors
        if "error" in result:
            report_blocks.append(f"⚠️ {name}: Error encountered during analysis.")
            continue

        # 2. Extract Analysis (Handles both JSON and raw string fallbacks)
        analysis = result.get("analysis", "")
        if not analysis and "findings" in result:  # Support for variations
            analysis = result["findings"]

        if analysis:
            report_blocks.append(f"🤖 {name} Analysis:\n   {analysis}")
            valid_agents += 1
            total_confidence += result.get("confidence", 0.8)

    # Final Summary Formatting
    avg_confidence = round(total_confidence / valid_agents, 2) if valid_agents > 0 else 0.0

    return {
        "structured_report": report_blocks,
        "agreement_level": "HIGH" if valid_agents >= 3 else "PARTIAL",
        "confidence": avg_confidence
    }
