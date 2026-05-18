def generate_reply(message: str) -> str:
    message = message.strip()
    if not message:
        return "Placeholder reply: no message received."

    return f"Placeholder reply to: {message}"
