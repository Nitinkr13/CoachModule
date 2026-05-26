from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from configs.loader import load_json_collection


@dataclass(frozen=True)
class PersonaConfig:
    id: str
    name: str
    description: str
    behavior: str
    cm_treatment: str
    evaluation_framework: str
    impact: str


@dataclass(frozen=True)
class ScenarioConfig:
    id: str
    name: str
    goal: str
    context: str
    evaluation_id: str
    template_id: str
    persona_behavior: dict = field(default_factory=dict)
    conversation_dynamics: dict = field(default_factory=dict)
    is_default: bool = False


@dataclass(frozen=True)
class EvaluationScale:
    min: int
    max: int
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationCriterion:
    id: str
    label: str
    description: str
    weight: float = 1.0


@dataclass(frozen=True)
class EvaluationConfig:
    id: str
    name: str
    scale: EvaluationScale
    criteria: List[EvaluationCriterion]


@dataclass(frozen=True)
class SimulationContext:
    persona: PersonaConfig
    scenario: ScenarioConfig
    evaluation: EvaluationConfig


_PERSONAS: Dict[str, PersonaConfig] = {}
_SCENARIOS: Dict[str, ScenarioConfig] = {}
_EVALUATIONS: Dict[str, EvaluationConfig] = {}


def _require(value: str, field_name: str, config_id: str) -> str:
    if not value:
        raise ValueError(f"Missing '{field_name}' in config '{config_id}'.")
    return value


def _ensure_unique_ids(items: List[str], label: str) -> None:
    if len(set(items)) != len(items):
        raise ValueError(f"Duplicate {label} ids found in configs.")


def _load_personas() -> Dict[str, PersonaConfig]:
    items = load_json_collection("personas")
    ids: List[str] = []
    personas: Dict[str, PersonaConfig] = {}

    for raw in items:
        persona_id = _require(str(raw.get("id", "")).strip(), "id", "persona")
        ids.append(persona_id)
        personas[persona_id] = PersonaConfig(
            id=persona_id,
            name=_require(str(raw.get("name", "")).strip(), "name", persona_id),
            description=str(raw.get("description", "")).strip(),
            behavior=str(raw.get("behavior", "")).strip(),
            cm_treatment=str(raw.get("cm_treatment", "")).strip(),
            evaluation_framework=str(raw.get("evaluation_framework", "")).strip(),
            impact=str(raw.get("impact", "")).strip(),
        )

    _ensure_unique_ids(ids, "persona")
    return personas


def _load_scenarios() -> Dict[str, ScenarioConfig]:
    items = load_json_collection("scenarios")
    ids: List[str] = []
    scenarios: Dict[str, ScenarioConfig] = {}

    for raw in items:
        scenario_id = _require(str(raw.get("id", "")).strip(), "id", "scenario")
        ids.append(scenario_id)
        scenarios[scenario_id] = ScenarioConfig(
            id=scenario_id,
            name=_require(str(raw.get("name", "")).strip(), "name", scenario_id),
            goal=str(raw.get("goal", "")).strip(),
            context=str(raw.get("context", "")).strip(),
            persona_behavior=raw.get("persona_behavior") or {},
            conversation_dynamics=raw.get("conversation_dynamics") or {},
            evaluation_id=str(raw.get("evaluation_id", "")).strip(),
            template_id=str(raw.get("template_id", "")).strip() or "live_session",
            is_default=bool(raw.get("is_default", False)),
        )

    _ensure_unique_ids(ids, "scenario")
    return scenarios


def _load_evaluations() -> Dict[str, EvaluationConfig]:
    items = load_json_collection("evaluations")
    ids: List[str] = []
    evaluations: Dict[str, EvaluationConfig] = {}

    for raw in items:
        evaluation_id = _require(str(raw.get("id", "")).strip(), "id", "evaluation")
        ids.append(evaluation_id)

        scale_raw = raw.get("scale") or {}
        scale = EvaluationScale(
            min=int(scale_raw.get("min", 1)),
            max=int(scale_raw.get("max", 5)),
            labels={str(k): str(v) for k, v in (scale_raw.get("labels") or {}).items()},
        )

        criteria: List[EvaluationCriterion] = []
        for criterion in raw.get("criteria") or []:
            criterion_id = _require(
                str(criterion.get("id", "")).strip(),
                "criteria.id",
                evaluation_id,
            )
            criteria.append(
                EvaluationCriterion(
                    id=criterion_id,
                    label=_require(
                        str(criterion.get("label", "")).strip(),
                        "criteria.label",
                        evaluation_id,
                    ),
                    description=str(criterion.get("description", "")).strip(),
                    weight=float(criterion.get("weight", 1.0) or 1.0),
                )
            )

        evaluations[evaluation_id] = EvaluationConfig(
            id=evaluation_id,
            name=str(raw.get("name", "")).strip() or evaluation_id,
            scale=scale,
            criteria=criteria,
        )

    _ensure_unique_ids(ids, "evaluation")
    return evaluations


def _ensure_loaded() -> None:
    if not _PERSONAS:
        _PERSONAS.update(_load_personas())
    if not _SCENARIOS:
        _SCENARIOS.update(_load_scenarios())
    if not _EVALUATIONS:
        _EVALUATIONS.update(_load_evaluations())


def list_personas() -> List[PersonaConfig]:
    _ensure_loaded()
    return list(_PERSONAS.values())


def get_persona(persona_id: str) -> Optional[PersonaConfig]:
    _ensure_loaded()
    return _PERSONAS.get(persona_id)


def get_scenario(scenario_id: str) -> Optional[ScenarioConfig]:
    _ensure_loaded()
    return _SCENARIOS.get(scenario_id)


def get_default_scenario() -> Optional[ScenarioConfig]:
    _ensure_loaded()
    for scenario in _SCENARIOS.values():
        if scenario.is_default:
            return scenario
    return next(iter(_SCENARIOS.values()), None)


def get_evaluation(evaluation_id: str) -> Optional[EvaluationConfig]:
    _ensure_loaded()
    return _EVALUATIONS.get(evaluation_id)


def resolve_simulation(
    persona_id: str,
    scenario_id: Optional[str] = None,
) -> SimulationContext:
    _ensure_loaded()

    persona = _PERSONAS.get(persona_id)
    if not persona:
        raise ValueError("Persona not found.")

    scenario = _SCENARIOS.get(scenario_id) if scenario_id else get_default_scenario()
    if not scenario:
        raise ValueError("Scenario not found.")

    evaluation = _EVALUATIONS.get(scenario.evaluation_id)
    if not evaluation:
        raise ValueError("Evaluation config not found.")

    return SimulationContext(persona=persona, scenario=scenario, evaluation=evaluation)
