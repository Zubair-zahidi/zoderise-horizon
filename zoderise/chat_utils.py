"""Small validated helpers shared by chat rendering and request preparation."""
import json


def object_list(value: object) -> list[dict]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return []
    if isinstance(value, dict):
        value = [value]
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def export_chat(messages) -> str:
    return "\n\n---\n\n".join(f"## {str(m['role']).title()}\n\n{m['content']}" for m in messages)
