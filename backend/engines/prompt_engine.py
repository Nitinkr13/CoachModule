def build_system_prompt(persona: dict, scenario: dict, template: str) -> str:
    persona_name = persona.get("name", "Unknown Persona")
    scenario_name = scenario.get("name", "Unknown Scenario")

    return (
        f"{template.strip()}\n\n"
        f"Persona: {persona_name}\n"
        f"Scenario: {scenario_name}\n"
    )
