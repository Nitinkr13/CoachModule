import json


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=True, indent=2)
        except TypeError:
            return str(value)
    return str(value)


def _read_value(source: object, key: str, default: str = "") -> str:
    if isinstance(source, dict):
        return _format_value(source.get(key, default) or default)
    return _format_value(getattr(source, key, default) or default)


def build_system_prompt(persona: dict, scenario: dict, template: str) -> str:
    persona_name = persona.get("name", "Unknown Persona")
    scenario_name = scenario.get("name", "Unknown Scenario")

    return (
        f"{template.strip()}\n\n"
        f"Persona: {persona_name}\n"
        f"Scenario: {scenario_name}\n"
    )


def build_live_system_prompt(role: str, context_text: str, template: str) -> str:
    return template.format(role=role, context=context_text).strip()


def build_simulation_prompt(persona: object, scenario: object, template: str) -> str:
    values = _SafeFormatDict(
        persona_name=_read_value(persona, "name"),
        persona_description=_read_value(persona, "description"),
        persona_behavior=_read_value(persona, "behavior"),
        cm_treatment=_read_value(persona, "cm_treatment"),
        impact=_read_value(persona, "impact"),
        scenario_name=_read_value(scenario, "name"),
        scenario_goal=_read_value(scenario, "goal"),
        scenario_context=_read_value(scenario, "context"),
        scenario_persona_behavior=_read_value(scenario, "persona_behavior"),
        scenario_conversation_dynamics=_read_value(scenario, "conversation_dynamics"),
    )

    return template.format_map(values).strip()
