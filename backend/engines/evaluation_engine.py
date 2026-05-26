from dataclasses import dataclass
import copy
import json
import os
import re
from typing import List, Optional

import requests

from app.env import load_env
from configs.loader import load_json
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
    feedback: str
    report: dict
    report_markdown: str
    rubric: List[EvaluationRubricItem]


_SBI_REPORT_TEMPLATE_NAME = "sbi_report_template"
_RUSH_REPORT_TEMPLATE_NAME = "rush_report_template"


def _normalize_framework(value: str) -> str:
    value = value.strip().upper()
    if value in {"SBI", "RUSH"}:
        return value
    return ""


def _select_framework(persona: PersonaConfig) -> str:
    explicit = _normalize_framework(persona.evaluation_framework)
    if explicit:
        return explicit

    treatment = persona.cm_treatment.lower()
    if "sbi" in treatment:
        return "SBI"
    if "rush" in treatment:
        return "RUSH"
    return "SBI"


def _report_template(framework: str) -> dict:
    if framework == "RUSH":
        return copy.deepcopy(load_json("evaluations/templates", _RUSH_REPORT_TEMPLATE_NAME))
    return copy.deepcopy(load_json("evaluations/templates", _SBI_REPORT_TEMPLATE_NAME))


def _build_prompt(
    persona: PersonaConfig,
    scenario: ScenarioConfig,
    evaluation: EvaluationConfig,
    history: List[EvaluationTurn],
    framework: str,
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

    report_template_json = json.dumps(
        _report_template(framework),
        ensure_ascii=True,
        indent=2,
    )

    return (
        "You are evaluating a coaching simulation session.\n"
        f"Persona name: {persona.name}\n"
        f"Persona description: {persona.description}\n"
        f"Persona behavior: {persona.behavior}\n"
        f"CM treatment guidance: {persona.cm_treatment}\n"
        f"Business impact: {persona.impact}\n"
        f"Selected framework: {framework}\n"
        f"Scenario name: {scenario.name}\n"
        f"Scenario goal: {scenario.goal}\n"
        f"Scenario context: {scenario.context}\n\n"
        f"Scenario persona behavior: {json.dumps(scenario.persona_behavior, ensure_ascii=True)}\n"
        f"Scenario conversation dynamics: {json.dumps(scenario.conversation_dynamics, ensure_ascii=True)}\n\n"
        "Evaluation scale:\n"
        f"- Min: {evaluation.scale.min}\n"
        f"- Max: {evaluation.scale.max}\n"
        f"- Labels: {scale_labels or 'None'}\n\n"
        "Criteria:\n"
        f"{chr(10).join(criteria_lines)}\n\n"
        "Conversation History:\n"
        f"{transcript}\n\n"
        "Report template (JSON):\n"
        f"{report_template_json}\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "- summary: string\n"
        "- overall_score: integer within the scale\n"
        "- rubric: array of {id, label, score, notes}\n"
        "- report: object that matches the report template structure exactly and fills every field\n"
        "- feedback: 2-4 sentence string based only on the Business impact above\n"
        "Leave every rating/overall_rating field in the report as null.\n"
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
        framework = _select_framework(persona)
        return EvaluationResult(
            score=evaluation.scale.min,
            summary="No conversation data available for evaluation.",
            feedback=persona.impact.strip() or "No impact details available.",
            report=_report_template(framework),
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
    framework = _select_framework(persona)
    prompt = _build_prompt(persona, scenario, evaluation, history, framework)
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
    report = data.get("report")
    if not isinstance(report, dict):
        report = data.get("evaluation_report_template")
        if isinstance(report, dict):
            report = {"evaluation_report_template": report}
        else:
            report = _report_template(framework)

    feedback = str(data.get("feedback", "")).strip()
    if not feedback:
        fallback = persona.impact.strip()
        feedback = fallback if fallback else "No impact feedback available."

    report_markdown = str(data.get("report_markdown", "")).strip()

    return EvaluationResult(
        score=score,
        summary=summary,
        feedback=feedback,
        report=report,
        report_markdown=report_markdown,
        rubric=rubric,
    )
