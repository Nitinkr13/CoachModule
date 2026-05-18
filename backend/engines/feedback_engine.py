def build_feedback(summary: str) -> str:
    summary = summary.strip() or "No summary provided."
    return f"Feedback: {summary}"
