"""
Mock LLM for Day 12 Lab. No real API key required.
"""
import random
import time


MOCK_RESPONSES = {
    "docker": [
        "Containers package app and dependencies so it runs consistently everywhere.",
    ],
    "redis": [
        "Redis stores fast shared state across instances for stateless scaling.",
    ],
    "default": [
        "This is a mock AI response. Replace with a real model provider in production.",
        "Your agent is running and processed the request successfully.",
        "Thanks for your question. Mock response generated for deployment practice.",
    ],
}


def ask(question: str, delay: float = 0.08) -> str:
    time.sleep(delay + random.uniform(0, 0.04))
    q = question.lower()
    for key, answers in MOCK_RESPONSES.items():
        if key != "default" and key in q:
            return random.choice(answers)
    return random.choice(MOCK_RESPONSES["default"])
