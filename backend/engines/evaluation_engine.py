from dataclasses import dataclass
import copy
import json
import logging
import os
import random
import re
import time
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
_SECTION_WEIGHTS = (0.3, 0.4, 0.3)
_DEFAULT_CONNECT_TIMEOUT_SEC = 10.0
_DEFAULT_READ_TIMEOUT_SEC = 180.0
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_RETRY_BASE_DELAY_SEC = 1.0
_DEFAULT_RETRY_MAX_DELAY_SEC = 8.0
_DEFAULT_FALLBACK_MODEL = "gemini-2.5-flash"

logger = logging.getLogger(__name__)


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
        "Populate rating fields for the three main sections (Setting the context, Used structured conversation approach, and Feedback/Conversation Skills) using integer scores within the scale.\n"
        "Compute overall_summary.overall_rating as a weighted average of those three section ratings using weights 0.3, 0.4, 0.3 (round to nearest integer within the scale).\n"
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


def _coerce_nullable_score(
    value: object,
    evaluation: EvaluationConfig,
) -> Optional[int]:
    if value is None:
        return None
    return _coerce_score(value, evaluation)


def _weighted_section_score(
    section_scores: List[Optional[int]],
    evaluation: EvaluationConfig,
) -> Optional[int]:
    total_weight = 0.0
    total_score = 0.0
    for score, weight in zip(section_scores, _SECTION_WEIGHTS):
        if score is None:
            continue
        total_weight += weight
        total_score += score * weight

    if total_weight == 0:
        return None

    average = total_score / total_weight
    return _coerce_score(round(average), evaluation)


def _normalize_report_ratings(
    report: dict,
    evaluation: EvaluationConfig,
) -> dict:
    if not isinstance(report, dict):
        return report

    template = report.get("evaluation_report_template")
    if not isinstance(template, dict):
        return report

    sections = template.get("sections")
    if not isinstance(sections, list):
        return report

    section_scores: List[Optional[int]] = []
    for idx, section in enumerate(sections):
        if idx >= len(_SECTION_WEIGHTS):
            break
        if not isinstance(section, dict):
            section_scores.append(None)
            continue
        rating = _coerce_nullable_score(section.get("rating"), evaluation)
        if rating is not None:
            section["rating"] = rating
        section_scores.append(rating)

    overall = template.get("overall_summary")
    if isinstance(overall, dict):
        computed = _weighted_section_score(section_scores, evaluation)
        if computed is not None:
            overall["overall_rating"] = computed
        else:
            overall_rating = _coerce_nullable_score(overall.get("overall_rating"), evaluation)
            if overall_rating is not None:
                overall["overall_rating"] = overall_rating

    return report


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


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _retry_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
) -> float:
    jitter = random.random() * 0.25 * base_delay
    delay = base_delay * (2 ** attempt) + jitter
    return min(delay, max_delay)


def _should_retry_status(status_code: int) -> bool:
    return status_code in {408, 429, 500, 502, 503, 504}


def _post_with_retry(
    primary_url: str,
    fallback_url: Optional[str],
    payload: dict,
    timeout: tuple[float, float],
    max_retries: int,
    base_delay: float,
    max_delay: float,
) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if attempt == 0 or not fallback_url:
                url = primary_url
            else:
                url = fallback_url
            response = requests.post(url, json=payload, timeout=timeout)
            if response.ok or not _should_retry_status(response.status_code):
                return response
            last_exc = RuntimeError(
                f"Gemini evaluation failed: {response.status_code} {response.text}"
            )
        except requests.exceptions.RequestException as exc:
            last_exc = exc

        if attempt < max_retries:
            delay = _retry_delay(attempt, base_delay, max_delay)
            logger.warning(
                "Gemini evaluation attempt %s failed; retrying in %.2fs",
                attempt + 1,
                delay,
            )
            time.sleep(delay)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Gemini evaluation failed with unknown error.")


def _fallback_evaluation(
    persona: PersonaConfig,
    evaluation: EvaluationConfig,
    framework: str,
    message: str,
) -> EvaluationResult:
    feedback = persona.impact.strip() or "No impact details available."
    return EvaluationResult(
        score=evaluation.scale.min,
        summary=message,
        feedback=feedback,
        report=_report_template(framework),
        report_markdown=message,
        rubric=_default_rubric(evaluation),
    )


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
    fallback_model = os.getenv("GEMINI_EVAL_FALLBACK_MODEL", _DEFAULT_FALLBACK_MODEL)
    connect_timeout = _get_float_env(
        "GEMINI_CONNECT_TIMEOUT_SEC",
        _DEFAULT_CONNECT_TIMEOUT_SEC,
    )
    read_timeout = _get_float_env(
        "GEMINI_READ_TIMEOUT_SEC",
        _DEFAULT_READ_TIMEOUT_SEC,
    )
    max_retries = _get_int_env("GEMINI_MAX_RETRIES", _DEFAULT_MAX_RETRIES)
    retry_base_delay = _get_float_env(
        "GEMINI_RETRY_BASE_DELAY_SEC",
        _DEFAULT_RETRY_BASE_DELAY_SEC,
    )
    retry_max_delay = _get_float_env(
        "GEMINI_RETRY_MAX_DELAY_SEC",
        _DEFAULT_RETRY_MAX_DELAY_SEC,
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    fallback_url = None
    if fallback_model:
        fallback_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{fallback_model}:generateContent?key={api_key}"
        )
    framework = _select_framework(persona)
    prompt = _build_prompt(persona, scenario, evaluation, history, framework)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = _post_with_retry(
            url,
            fallback_url,
            payload,
            (connect_timeout, read_timeout),
            max_retries,
            retry_base_delay,
            retry_max_delay,
        )
        if not response.ok:
            raise RuntimeError(
                f"Gemini evaluation failed: {response.status_code} {response.text}"
            )

        raw_text = _extract_report_text(response.json()).strip()
        if not raw_text:
            raise RuntimeError("Gemini evaluation returned empty response.")
    except Exception as exc:
        logger.exception("Gemini evaluation failed, returning fallback.")
        return _fallback_evaluation(
            persona,
            evaluation,
            framework,
            "Evaluation temporarily unavailable. Please retry.",
        )

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

    report = _normalize_report_ratings(report, evaluation)

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
