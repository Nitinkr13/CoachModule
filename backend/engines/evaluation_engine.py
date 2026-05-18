from dataclasses import dataclass
import os
import re
from typing import List

import requests

from app.env import load_env
from models.schemas import EvaluationTurn


@dataclass
class EvaluationResult:
    score: int
    summary: str
    report_markdown: str


def _build_prompt(role: str, file_name: str, history: List[EvaluationTurn]) -> str:
    transcript = "\n".join([f"{turn.speaker}: {turn.text}" for turn in history])

    return (
        "Evaluate the training session performance of the User.\n"
        f"The User interacted with an AI acting as: {role}\n"
        f"Reference context provided: {file_name}\n"
        "(It was a voice interaction, and you are evaluating the User's performance based on the conversation history below.)\n\n"
        "Conversation History:\n"
        f"{transcript}\n\n"
        "Provide a detailed report in Markdown format:\n"
        "1. # Session Summary (A high-level overview of the interaction)\n"
        "2. ## Performance Highlights (What the user did well)\n"
        "3. ## Growth Opportunities (Areas for improvement)\n"
        "4. ## Recommended Strategy (3 specific tips for future sessions)\n"
        "5. ## Final Score: [Score]/10\n\n"
        "Use bold text, lists, and clear headings."
    )


def _extract_score(report_markdown: str) -> int:
    match = re.search(r"Final Score:\s*(\d{1,2})\s*/\s*10", report_markdown, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def _extract_report_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        return ""

    return parts[0].get("text") or ""


def evaluate_session(role: str, file_name: str, history: List[EvaluationTurn]) -> EvaluationResult:
    if not history:
        return EvaluationResult(
            score=0,
            summary="No conversation data available for evaluation.",
            report_markdown="No conversation data available for evaluation.",
        )

    load_env()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY on server.")

    model = os.getenv("GEMINI_EVAL_MODEL", "gemini-3-flash-preview")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    prompt = _build_prompt(role, file_name, history)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=60)
    if not response.ok:
        raise RuntimeError(
            f"Gemini evaluation failed: {response.status_code} {response.text}"
        )

    report_markdown = _extract_report_text(response.json()).strip()
    if not report_markdown:
        raise RuntimeError("Gemini evaluation returned empty response.")

    score = _extract_score(report_markdown)
    summary = "Performance report generated."
    return EvaluationResult(score=score, summary=summary, report_markdown=report_markdown)
