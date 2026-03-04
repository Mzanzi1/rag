# C:\AI Projects\rag2\agents.py
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("QDRANT_BUILDER_URL")
API_TOKEN = os.getenv("QDRANT_BUILDER_API")


def call_agent(agent_cfg, context, query):
    agent_name = agent_cfg['name']

    # 1. Clean and trim context (4 segments, 500 chars each)
    context_parts = []
    for c in context[:4]:
        body = c.get('body', '')
        if '---------' in body: body = body.split('---------')[0]
        context_parts.append(f"Subject: {c.get('subject')}\nInfo: {body[:500]}")
    context_text = "\n\n".join(context_parts)

    # 2. Setup the Samsung Agent Builder Payload
    payload = {
        "input_type": "chat",
        "output_type": "chat",
        "input_value": f"Role: {agent_name}. Focus: {agent_cfg['focus']}. Query: {query}\n\nDATA:\n{context_text}"
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_TOKEN
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            return {"agent": agent_name, "analysis": f"Error {response.status_code}"}

        data = response.json()

        # 3. Precise extraction from Samsung Agent Builder JSON structure
        try:
            # Path: outputs[0] -> outputs[0] -> results -> message -> text
            ans = data['outputs'][0]['outputs'][0]['results']['message']['text']
        except (KeyError, IndexError):
            # Try a slightly flatter fallback just in case
            ans = data.get('output_value', str(data))

        return {"agent": agent_name, "analysis": ans}

    except Exception as e:
        return {"agent": agent_name, "error": str(e)}
