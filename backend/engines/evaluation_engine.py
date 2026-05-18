from dataclasses import dataclass
import json
import os
import re
from typing import List, Optional

import requests

from app.env import load_env
from engines.simulation_engine import (
    EvaluationConfig,
    EvaluationCriterion,
    PersonaConfig,
    ScenarioConfig,
)
from models.schemas import EvaluationTurn


@dataclass
class EvaluationRubricItem:
    id: str
    label: str
    score: int
    notes: str


@dataclass
class EvaluationResult:
    score: int
    summary: str
    report_markdown: str
    rubric: List[EvaluationRubricItem]


def _build_prompt(
    persona: PersonaConfig,
    scenario: ScenarioConfig,
    evaluation: EvaluationConfig,
    history: List[EvaluationTurn],
) -> str:
    transcript = "\n".join([f"{turn.speaker}: {turn.text}" for turn in history])

    criteria_lines = []
    for criterion in evaluation.criteria:
        criteria_lines.append(
            f"- {criterion.id}: {criterion.label} - {criterion.description}"
        )

    scale_labels = ", ".join(
        [f"{k}={v}" for k, v in evaluation.scale.labels.items()]
    )

    return (
        "You are evaluating a coaching simulation session.\n"
        f"Persona name: {persona.name}\n"
        f"Persona behavior: {persona.behavior}\n"
        f"CM treatment guidance: {persona.cm_treatment}\n"
        f"Business impact: {persona.impact}\n"
        f"Scenario name: {scenario.name}\n"
        f"Scenario goal: {scenario.goal}\n"
        f"Scenario context: {scenario.context}\n\n"
        "Evaluation scale:\n"
        f"- Min: {evaluation.scale.min}\n"
        f"- Max: {evaluation.scale.max}\n"
        f"- Labels: {scale_labels or 'None'}\n\n"
        "Criteria:\n"
        f"{chr(10).join(criteria_lines)}\n\n"
        "Conversation History:\n"
        f"{transcript}\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "- summary: string\n"
        "- overall_score: integer within the scale\n"
        "- rubric: array of {id, label, score, notes}\n"
        "- report_markdown: markdown string with headings for summary, highlights, growth, and next steps\n"
        "Ensure rubric scores are integers within the scale and include every criterion id listed above."
    )


def _extract_report_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        return ""

    return parts[0].get("text") or ""


def _extract_json_block(text: str) -> Optional[dict]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else None
    if not candidate:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]

    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _coerce_score(value: object, evaluation: EvaluationConfig) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = evaluation.scale.min
    return max(evaluation.scale.min, min(evaluation.scale.max, score))


def _default_rubric(evaluation: EvaluationConfig) -> List[EvaluationRubricItem]:
    return [
        EvaluationRubricItem(
            id=criterion.id,
            label=criterion.label,
            score=evaluation.scale.min,
            notes="",
        )
        for criterion in evaluation.criteria
    ]


def _normalize_rubric(
    data: dict,
    evaluation: EvaluationConfig,
) -> List[EvaluationRubricItem]:
    raw_rubric = data.get("rubric") or []
    by_id: dict[str, dict] = {}
    by_label: dict[str, dict] = {}
    for item in raw_rubric:
        item_id = str(item.get("id", "")).strip()
        item_label = str(item.get("label", "")).strip()
        if item_id:
            by_id[item_id] = item
        if item_label:
            by_label[item_label.lower()] = item

    normalized: List[EvaluationRubricItem] = []
    for criterion in evaluation.criteria:
        raw = by_id.get(criterion.id) or by_label.get(criterion.label.lower()) or {}
        normalized.append(
            EvaluationRubricItem(
                id=criterion.id,
                label=criterion.label,
                score=_coerce_score(raw.get("score"), evaluation),
                notes=str(raw.get("notes", "")).strip(),
            )
        )
    return normalized


def _compute_overall(
    rubric: List[EvaluationRubricItem],
    criteria: List[EvaluationCriterion],
    evaluation: EvaluationConfig,
) -> int:
    if not rubric:
        return evaluation.scale.min

    weights = {criterion.id: criterion.weight for criterion in criteria}
    total_weight = sum(weights.values()) or len(rubric)
    total_score = 0.0
    for item in rubric:
        total_score += item.score * weights.get(item.id, 1.0)

    average = total_score / total_weight
    return _coerce_score(round(average), evaluation)


def evaluate_session(
    persona: PersonaConfig,
    scenario: ScenarioConfig,
    evaluation: EvaluationConfig,
    history: List[EvaluationTurn],
) -> EvaluationResult:
    if not history:
        return EvaluationResult(
            score=evaluation.scale.min,
            summary="No conversation data available for evaluation.",
            report_markdown="No conversation data available for evaluation.",
            rubric=_default_rubric(evaluation),
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
    prompt = _build_prompt(persona, scenario, evaluation, history)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=60)
    if not response.ok:
        raise RuntimeError(
            f"Gemini evaluation failed: {response.status_code} {response.text}"
        )

    raw_text = _extract_report_text(response.json()).strip()
    if not raw_text:
        raise RuntimeError("Gemini evaluation returned empty response.")

    data = _extract_json_block(raw_text) or {}
    rubric = _normalize_rubric(data, evaluation)
    if "overall_score" in data:
        score = _coerce_score(data.get("overall_score"), evaluation)
    else:
        score = _compute_overall(rubric, evaluation.criteria, evaluation)

    summary = str(data.get("summary", "Performance report generated.")).strip()
    report_markdown = str(data.get("report_markdown", "")).strip() or raw_text

    return EvaluationResult(
        score=score,
        summary=summary,
        report_markdown=report_markdown,
        rubric=rubric,
    )
